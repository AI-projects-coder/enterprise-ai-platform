import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UsageEvent(Base):
    """One row per LLM call (not per chat message — a single chat turn with
    tool calls produces multiple generate() calls, each its own billed
    request to Gemini, so each gets its own row). This is the source of
    truth for token/cost analytics; Cloud Logging (phase 7) covers
    operational debugging of the same calls but isn't queryable from the
    app itself and isn't retained the same way."""

    __tablename__ = "usage_events"
    __table_args__ = {"schema": "analytics"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    response_tokens: Mapped[int] = mapped_column(Integer, default=0)
    thoughts_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
