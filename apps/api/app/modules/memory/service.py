import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models import Conversation, Message


async def create_conversation(
    db: AsyncSession, user_id: uuid.UUID, title: str | None = None
) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def get_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation | None:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        return None
    return conversation


async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[Conversation]:
    result = await db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result)


async def add_message(
    db: AsyncSession, conversation_id: uuid.UUID, role: str, content: str
) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)

    conversation = await db.get(Conversation, conversation_id)
    conversation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(message)
    return message


async def list_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[Message]:
    """Full-fidelity history, including tool_call/tool_result turns — used to
    rebuild LLM context (agents/service.py), never sent straight to a client."""
    result = await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result)


DISPLAY_ROLES = ("user", "assistant")


async def list_display_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[Message]:
    """User-facing subset — hides tool_call/tool_result turns from the chat
    UI. Surfacing them (e.g. "🔍 searched knowledge base") is a reasonable
    future feature for the Monitoring/Analytics phase, not built here."""
    result = await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role.in_(DISPLAY_ROLES))
        .order_by(Message.created_at)
    )
    return list(result)
