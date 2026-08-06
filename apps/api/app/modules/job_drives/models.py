import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class JobDrive(Base):
    __tablename__ = "job_drives"
    __table_args__ = {"schema": "job_drives"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), index=True)
    # role/city/experience_band are plain strings, NOT a fixed backend enum
    # (unlike auth.User.profession) — the user explicitly wants to add more
    # dropdown options incrementally over time, and nothing here branches
    # application logic on the specific value the way profession will for
    # future role-based features. These are just search parameters fed into
    # a prompt, so the fixed list only needs to live in the frontend
    # dropdown — adding a city later is a frontend-only change, no backend
    # redeploy or migration required.
    role: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    experience_band: Mapped[str] = mapped_column(String(20))
    # Gemini's grounded response, stored as markdown and rendered as
    # markdown — same pattern as every other AI-generated text in this app
    # (chat replies, security reviews, cost estimates), not parsed into
    # structured per-drive fields.
    generated_content: Mapped[str] = mapped_column(Text)
    # "draft" -> "published". A draft is only visible to its creator; see
    # job_drives/service.py::list_job_drives.
    status: Mapped[str] = mapped_column(String(20), default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
