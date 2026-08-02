from fastapi import FastAPI

from app.modules.ai_gateway.router import router as ai_gateway_router
from app.modules.auth.router import router as auth_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.memory.router import router as memory_router

app = FastAPI(title="Enterprise AI Platform API")

app.include_router(auth_router)
app.include_router(ai_gateway_router)
app.include_router(memory_router)
app.include_router(knowledge_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
