import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.models import UsageEvent
from app.modules.analytics.schemas import DailyUsage, MemberUsage, OrgUsageSummary, UsageSummary
from app.modules.auth.models import User
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


async def get_org_usage_summary(db: AsyncSession, org_id: uuid.UUID, since_days: int = 30) -> OrgUsageSummary:
    """Only meaningful now that org membership is real (phase 9) — phase 8
    deliberately didn't build this because org_id was a stub with no actual
    members behind it. Two grouped queries (not one N+1 loop per member) so
    this stays reasonable as a team grows."""
    since = datetime.now(timezone.utc) - timedelta(days=since_days)

    members = list(await db.scalars(select(User).where(User.org_id == org_id).order_by(User.created_at)))
    member_ids = [m.id for m in members]

    message_counts = dict(
        (
            await db.execute(
                select(Conversation.user_id, func.count(Message.id))
                .join(Message, Message.conversation_id == Conversation.id)
                .where(
                    Conversation.user_id.in_(member_ids),
                    Message.role == "user",
                    Message.created_at >= since,
                )
                .group_by(Conversation.user_id)
            )
        ).all()
    )

    usage_by_user = {
        row[0]: (row[1], row[2])
        for row in (
            await db.execute(
                select(
                    UsageEvent.user_id,
                    func.count(UsageEvent.id),
                    func.coalesce(func.sum(UsageEvent.total_tokens), 0),
                )
                .where(UsageEvent.user_id.in_(member_ids), UsageEvent.created_at >= since)
                .group_by(UsageEvent.user_id)
            )
        ).all()
    }

    member_usages = []
    total_messages = 0
    total_tokens = 0
    for member in members:
        msg_count = message_counts.get(member.id, 0)
        llm_count, tokens = usage_by_user.get(member.id, (0, 0))
        member_usages.append(
            MemberUsage(
                user_id=member.id,
                email=member.email,
                message_count=msg_count,
                llm_call_count=llm_count,
                total_tokens=tokens,
            )
        )
        total_messages += msg_count
        total_tokens += tokens

    return OrgUsageSummary(
        since_days=since_days,
        member_count=len(members),
        total_message_count=total_messages,
        total_tokens=total_tokens,
        members=member_usages,
    )
