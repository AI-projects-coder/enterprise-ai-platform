from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.agents.service import run_chat
from app.modules.ai_gateway.schemas import ChatRequest, ChatResponse
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Orchestration (tool-calling loop across ai_gateway/knowledge/memory)
    # lives in agents/service.py now, not here — see
    # docs/architecture/0005-agent-tool-calling.md for why this replaced the
    # phase-4 always-on retrieval that used to live in this router.
    return await run_chat(db, current_user.id, data)
