import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.models import UsageEvent
from app.modules.analytics.schemas import DailyUsage, UsageSummary
from app.modules.knowledge.models import Document
from app.modules.memory.models import Conversation, Message


async def record_usage_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    model: str,
    prompt_tokens: int,
    response_tokens: int,
    thoughts_tokens: int,
    total_tokens: int,
) -> None:
    db.add(
        UsageEvent(
            user_id=user_id,
            event_type=event_type,
            model=model,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            thoughts_tokens=thoughts_tokens,
            total_tokens=total_tokens,
        )
    )
    await db.commit()


async def get_usage_summary(db: AsyncSession, user_id: uuid.UUID, since_days: int = 30) -> UsageSummary:
    """Conversation/message/document counts are computed live from memory's
    and knowledge's own tables (they're already the source of truth for
    that data — no reason to duplicate it). Token/cost figures come from
    usage_events, the one piece of data that didn't exist anywhere in
    Postgres before this module."""
    since = datetime.now(timezone.utc) - timedelta(days=since_days)

    conversation_count = await db.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.user_id == user_id, Conversation.created_at >= since
        )
    )

    message_count = await db.scalar(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id, Message.role == "user", Message.created_at >= since)
    )

    document_count = await db.scalar(
        select(func.count(Document.id)).where(Document.user_id == user_id, Document.created_at >= since)
    )

    llm_call_count, total_tokens = (
        await db.execute(
            select(func.count(UsageEvent.id), func.coalesce(func.sum(UsageEvent.total_tokens), 0)).where(
                UsageEvent.user_id == user_id, UsageEvent.created_at >= since
            )
        )
    ).one()

    daily_rows = await db.execute(
        select(
            func.date(UsageEvent.created_at).label("day"),
            func.count(UsageEvent.id),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0),
        )
        .where(UsageEvent.user_id == user_id, UsageEvent.created_at >= since)
        .group_by(func.date(UsageEvent.created_at))
        .order_by(func.date(UsageEvent.created_at))
    )

    return UsageSummary(
        since_days=since_days,
        conversation_count=conversation_count or 0,
        message_count=message_count or 0,
        document_count=document_count or 0,
        llm_call_count=llm_call_count or 0,
        total_tokens=total_tokens or 0,
        daily=[DailyUsage(day=row[0], llm_calls=row[1], total_tokens=row[2]) for row in daily_rows],
    )
