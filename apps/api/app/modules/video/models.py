import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = {"schema": "video"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    storage_ref: Mapped[str] = mapped_column(String(500))
    # "processing" -> "ready" | "failed". No polling/websocket in v1 — the
    # frontend just shows this on next page load, same simplification as
    # the rest of this phase (see video/service.py docstring).
    status: Mapped[str] = mapped_column(String(20), default="processing")
    # Set once analyze_video()'s output has been chunked+embedded via
    # knowledge.ingest_document — this IS the video's searchable content,
    # reusing phase 4's pipeline rather than building a parallel one.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge.documents.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
