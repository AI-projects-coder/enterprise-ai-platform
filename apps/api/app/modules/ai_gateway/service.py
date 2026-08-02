import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Literal, NoReturn

from fastapi import HTTPException, status
from google import genai
from google.genai import errors, types

from app.modules.ai_gateway.schemas import ToolDeclaration
from app.modules.memory.models import Message

MODEL = "gemini-3.6-flash"
EMBED_MODEL = "gemini-embedding-2"

logger = logging.getLogger("app.llm")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def _check_configured() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI Gateway is not configured (missing GEMINI_API_KEY)",
        )


def _handle_api_error(e: errors.APIError) -> NoReturn:
    # Gemini returns 400 INVALID_ARGUMENT for a bad key, not 401/403 —
    # verified against a live call, not assumed from REST convention.
    if e.code in (400, 401, 403) and "api key" in e.message.lower():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI Gateway is not configured (invalid GEMINI_API_KEY)",
        ) from e
    raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Gemini API error: {e.message}") from e


@dataclass
class GenerateResult:
    """Provider-neutral result — agents/service.py never touches google.genai
    types directly, only this module does."""

    kind: Literal["text", "tool_calls"]
    text: str | None = None
    calls: list[dict] | None = None


async def embed(text: str) -> list[float]:
    """Called from ai_gateway itself (query embedding, via the search_knowledge
    tool) and from knowledge (chunk embedding at ingestion) — an independent
    entry point, not just a helper inside a chat request, so it checks
    configuration itself."""
    _check_configured()

    start = time.perf_counter()
    try:
        response = await _get_client().aio.models.embed_content(model=EMBED_MODEL, contents=text)
    except errors.APIError as e:
        logger.error(
            "embed_failed",
            extra={
                "model": EMBED_MODEL,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "gemini_error": e.message,
            },
        )
        _handle_api_error(e)

    logger.info(
        "embed_completed",
        extra={
            "model": EMBED_MODEL,
            "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            "input_chars": len(text),
        },
    )
    return response.embeddings[0].values


def _build_contents(history: list[Message]) -> list[types.Content]:
    """Memory stores roles/content provider-neutrally (see memory/models.py);
    this is the only place that knows Gemini calls the assistant turn "model",
    and that a tool-calling round-trip is two Gemini turns (a model turn with
    function_call parts, then a user turn with function_response parts) —
    verified against the installed SDK's own automatic-function-calling
    implementation (_extra_utils.py), not guessed."""
    contents = []
    for m in history:
        if m.role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m.content)]))
        elif m.role == "assistant":
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=m.content)]))
        elif m.role == "tool_call":
            calls = json.loads(m.content)
            parts = []
            for c in calls:
                part = types.Part.from_function_call(name=c["name"], args=c["args"])
                # Gemini 3 requires replaying the exact thought_signature that
                # came back on the original function_call part, or it rejects
                # the request outright ("missing thought_signature") — caught
                # by a live call, not documented anywhere we read up front.
                if c.get("thought_signature"):
                    part.thought_signature = base64.b64decode(c["thought_signature"])
                parts.append(part)
            contents.append(types.Content(role="model", parts=parts))
        elif m.role == "tool_result":
            results = json.loads(m.content)
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(name=r["name"], response=r["response"])
                        for r in results
                    ],
                )
            )
    return contents


async def generate(history: list[Message], tools: list[ToolDeclaration] | None = None) -> GenerateResult:
    _check_configured()

    contents = _build_contents(history)

    config = None
    if tools:
        # Only declarations go to Gemini — no callables, so the SDK's
        # automatic function calling never activates (it only wraps plain
        # Python callables passed in `tools`, verified in _extra_utils.py's
        # get_function_map). Execution stays entirely in agents/service.py,
        # which is the only place with the request's db session and user_id.
        declarations = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=t.name, description=t.description, parameters_json_schema=t.parameters
                )
                for t in tools
            ]
        )
        config = types.GenerateContentConfig(tools=[declarations])

    start = time.perf_counter()
    try:
        response = await _get_client().aio.models.generate_content(model=MODEL, contents=contents, config=config)
    except errors.APIError as e:
        logger.error(
            "generate_failed",
            extra={
                "model": MODEL,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "tools_offered": bool(tools),
                "gemini_error": e.message,
            },
        )
        _handle_api_error(e)

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    usage = response.usage_metadata
    log_fields = {
        "model": MODEL,
        "duration_ms": duration_ms,
        "tools_offered": bool(tools),
        # Token counts are the actual cost signal for an LLM-backed
        # endpoint — thoughts_token_count matters specifically for Gemini 3,
        # whose extended thinking is billed as output tokens too.
        "prompt_tokens": usage.prompt_token_count if usage else None,
        "response_tokens": usage.candidates_token_count if usage else None,
        "thoughts_tokens": usage.thoughts_token_count if usage else None,
        "total_tokens": usage.total_token_count if usage else None,
    }

    if response.function_calls:
        # Walk the raw parts (not the response.function_calls convenience
        # property) because that property returns only FunctionCall objects
        # and drops each part's thought_signature — which _build_contents
        # needs to replay on the next turn.
        response_parts = response.candidates[0].content.parts
        calls = [
            {
                "name": p.function_call.name,
                "args": p.function_call.args or {},
                "thought_signature": base64.b64encode(p.thought_signature).decode()
                if p.thought_signature
                else None,
            }
            for p in response_parts
            if p.function_call is not None
        ]
        logger.info(
            "generate_completed",
            extra={**log_fields, "outcome": "tool_calls", "tool_call_count": len(calls)},
        )
        return GenerateResult(kind="tool_calls", calls=calls)

    logger.info("generate_completed", extra={**log_fields, "outcome": "text"})
    return GenerateResult(kind="text", text=response.text or "")
