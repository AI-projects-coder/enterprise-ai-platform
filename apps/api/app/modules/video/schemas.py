import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.ai_gateway.service import VideoQuizQuestion, VideoTranscriptSegment


class VideoRead(BaseModel):
    """Library card / list view — deliberately excludes transcript/summary/
    quiz payloads, which can be large; those load only on the page that
    actually needs them, via VideoDetail."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    content_type: str
    status: str
    visibility: str
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoDetail(VideoRead):
    transcript_segments: list[VideoTranscriptSegment] | None
    summary_notes: str | None
    key_points: list[str] | None
    quiz: list[VideoQuizQuestion] | None
    playback_url: str


class UploadUrlRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    content_type: str = "video/mp4"


class UploadUrlResponse(BaseModel):
    # Both are None together when GCS isn't configured (local dev) — no row
    # was created, and the caller must fall back to POST /videos/local-upload
    # (multipart) instead of PUTting here.
    video_id: uuid.UUID | None
    upload_url: str | None


class FromLinkRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    source_url: str = Field(min_length=1)


class PlaybackUrlResponse(BaseModel):
    playback_url: str


class VideoEventCreate(BaseModel):
    event_type: Literal["play", "pause", "complete", "qa_click", "summary_click"]
    watch_duration_seconds: float | None = None
    completion_pct: float | None = None
