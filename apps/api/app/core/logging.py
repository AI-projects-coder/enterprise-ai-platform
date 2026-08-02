import contextvars
import json
import logging
import sys
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# contextvars (not a plain module-level variable) because this must stay
# correct under concurrent requests — asyncio interleaves coroutines on one
# thread, so a plain global would leak one request's id into another's logs.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)

# Standard attributes every LogRecord carries — anything else on the record
# came from `extra={...}` at the call site and should be surfaced in the
# JSON payload as its own field.
_STANDARD_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
    "color_message",  # uvicorn-internal, ANSI codes for its own console output
}


class JsonFormatter(logging.Formatter):
    """"severity" and "message" are the exact field names Cloud Run's logging
    agent looks for to populate a LogEntry's severity/message instead of
    dumping the whole line into an opaque textPayload — verified against
    Cloud Run's structured logging docs, not assumed from a generic JSON
    logger. Locally this is still just readable JSON on stdout."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        user_id = user_id_var.get()
        if user_id:
            payload["user_id"] = user_id

        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    # uvicorn's own loggers print plain text by default and bypass the root
    # handler (propagate=True doesn't help — they add their own handler);
    # point them at the same JSON handler instead of leaving two log formats
    # mixed together in Cloud Logging.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = [handler]
        uv_logger.propagate = False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Replaces uvicorn's plain-text access log with one structured line per
    request, correlated to any other log lines emitted during that request
    (e.g. the Gemini call logging in ai_gateway) via request_id."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request_token = request_id_var.set(request_id)
        user_token = user_id_var.set(None)
        start = time.perf_counter()
        logger = logging.getLogger("app.request")

        # Context vars are reset AFTER logging in both branches below, not in
        # a `finally` here — resetting first would strip request_id/user_id
        # from the very log line that most needs them for correlation.
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            request_id_var.reset(request_token)
            user_id_var.reset(user_token)
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-Id"] = request_id

        # Severity tracks status code so Cloud Logging/Monitoring can filter
        # or alert on severity>=ERROR and only catch actual failures, not
        # routine 404s.
        level = logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING

        logger.log(
            level,
            "request_handled",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        request_id_var.reset(request_token)
        user_id_var.reset(user_token)
        return response
