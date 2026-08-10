import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = {"schema": "video"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    storage_ref: Mapped[str] = mapped_column(String(500), default="")
    content_type: Mapped[str] = mapped_column(String(100), default="video/mp4")
    # "processing" -> "ready" | "failed" — the analysis pipeline's state.
    status: Mapped[str] = mapped_column(String(20), default="processing")
    # "draft" (owner-only) -> "published" (everyone's library) — kept as its
    # own column, independent of `status` above, same two-axis split
    # job_drives uses for its own draft/publish gate.
    visibility: Mapped[str] = mapped_column(String(20), default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Set once analyze()'s output has been chunked+embedded via
    # knowledge.ingest_document, so video content stays searchable via the
    # existing search_knowledge chat tool with zero new agent-tool code.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge.documents.id"), default=None
    )
    # One combined Gemini call's output (ai_gateway.analyze_video), generated
    # once at upload time and never regenerated — Q&A/Summary/Play all read
    # from these same three columns instead of calling Gemini per page view.
    # transcript_segments: [{start_seconds, end_seconds, text}, ...]
    # quiz: [{question, type, options, correct_indices}, ...]
    transcript_segments: Mapped[list | None] = mapped_column(JSON, default=None)
    summary_notes: Mapped[str | None] = mapped_column(Text, default=None)
    key_points: Mapped[list | None] = mapped_column(JSON, default=None)
    quiz: Mapped[list | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class VideoEvent(Base):
    """Raw watch-behavior log — one row per play/pause/complete/click event,
    written now and read by nobody yet. Exists so the future recommendation
    engine has real history to train on from day one instead of a cold
    start once it's actually built."""

    __tablename__ = "video_events"
    __table_args__ = {"schema": "video"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), index=True)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("video.videos.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    watch_duration_seconds: Mapped[float | None] = mapped_column(Float, default=None)
    completion_pct: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
