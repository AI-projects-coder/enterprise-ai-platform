from fastapi import FastAPI

from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.modules.ai_gateway.router import router as ai_gateway_router
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.enterprise.router import router as enterprise_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.memory.router import router as memory_router

configure_logging()

app = FastAPI(title="Enterprise AI Platform API")
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(enterprise_router)
app.include_router(ai_gateway_router)
app.include_router(memory_router)
app.include_router(knowledge_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
