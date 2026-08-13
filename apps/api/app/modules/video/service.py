import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import SessionLocal
from app.modules.ai_gateway.service import VideoAnalysis, analyze_video
from app.modules.knowledge.service import ingest_document
from app.modules.video.models import Video, VideoEvent

logger = logging.getLogger("app.video")

# Local-dev-only fallback cap (see create_local_upload) — the presigned GCS
# path used in every deployed env has no such limit, since bytes never pass
# through this API's memory at all.
MAX_VIDEO_SIZE = 20 * 1024 * 1024
LINK_DOWNLOAD_TIMEOUT = 120.0


def _flatten_for_search(analysis: VideoAnalysis) -> str:
    """Turns the structured analysis back into plain text for
    knowledge.ingest_document — chat search wants prose to chunk/embed, not
    the structured fields the library UI reads directly off the Video row."""
    transcript_text = " ".join(segment.text for segment in analysis.transcript)
    key_points_text = "\n".join(f"- {point}" for point in analysis.key_points)
    return f"{analysis.summary}\n\nKey points:\n{key_points_text}\n\nTranscript:\n{transcript_text}"


async def _analyze_and_save(db: AsyncSession, video: Video, user_id: uuid.UUID, content: bytes) -> None:
    analysis = await analyze_video(content, video.content_type)
    document = await ingest_document(db, user_id, video.title, _flatten_for_search(analysis))

    video.transcript_segments = [s.model_dump() for s in analysis.transcript]
    video.summary_notes = analysis.summary
    video.key_points = analysis.key_points
    video.quiz = [q.model_dump() for q in analysis.quiz]
    video.document_id = document.id
    video.status = "ready"
    await db.commit()


async def create_upload_target(
    db: AsyncSession, user_id: uuid.UUID, title: str, description: str, content_type: str
) -> tuple[Video | None, str | None]:
    """Only creates a row when GCS is actually configured — checked BEFORE
    creating anything, not after. Getting this order wrong (create the row,
    then discover there's no GCS) is what caused every local-dev upload to
    produce two rows: this throwaway one plus the real one from the
    local-upload fallback the frontend calls next. When GCS isn't
    configured, returns (None, None) — the frontend's local-upload fallback
    is then the ONLY path that creates a row.

    Commit is deliberately the LAST step, after signing succeeds — not
    before. flush() assigns video.id (needed as the signed URL's blob key)
    without committing, so if presigned_upload_url() throws (hit live in
    sandbox: a private-key signing error), the `async with SessionLocal()`
    block in get_db rolls the whole thing back automatically and no orphaned
    row is left behind stuck in "processing" forever."""
    if not storage.GCS_BUCKET:
        return None, None

    video = Video(
        user_id=user_id, title=title, description=description, content_type=content_type
    )
    db.add(video)
    await db.flush()

    upload_url = await storage.presigned_upload_url(video.id, content_type, folder="videos")

    await db.commit()
    await db.refresh(video)
    return video, upload_url


async def confirm_upload(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID) -> Video:
    """Called once the browser's direct PUT to the presigned URL succeeds —
    the API never saw the bytes, so this just records where they landed and
    hands back the video for the router to schedule analysis on."""
    video = await db.get(Video, video_id)
    if video is None or video.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")

    video.storage_ref = f"gs://{storage.GCS_BUCKET}/videos/{video.id}"
    await db.commit()
    await db.refresh(video)
    return video


async def create_local_upload(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str,
    description: str,
    content: bytes,
    content_type: str,
) -> Video:
    """Local-dev-only fallback for environments without GCS configured (same
    direct-through-API path the video module used before this rebuild),
    capped at MAX_VIDEO_SIZE since the whole file is buffered in memory."""
    if len(content) > MAX_VIDEO_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Video too large ({len(content)} bytes) — max {MAX_VIDEO_SIZE} bytes for local dev",
        )

    video = Video(
        user_id=user_id, title=title, description=description, content_type=content_type
    )
    db.add(video)
    await db.flush()  # assigns video.id before it's needed as the storage key

    video.storage_ref = await storage.save(video.id, content, content_type, folder="videos")
    await db.commit()
    await db.refresh(video)
    return video


async def create_from_link(
    db: AsyncSession, user_id: uuid.UUID, title: str, description: str, source_url: str
) -> Video:
    """Creates the row immediately (status stays 'processing'); the actual
    download+analysis happens in process_from_link after the response is
    sent, same reasoning as the upload paths — a slow source server
    shouldn't make this request itself time out."""
    video = Video(user_id=user_id, title=title, description=description)
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


async def process_upload(video_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Runs via FastAPI BackgroundTasks after a presigned-upload confirm —
    needs its own db session, since the request's session is closed by the
    time this runs (same reasoning as the original process_video)."""
    async with SessionLocal() as db:
        video = await db.get(Video, video_id)
        try:
            content = await storage.load(video.storage_ref)
            await _analyze_and_save(db, video, user_id, content)
        except Exception:
            logger.exception("video_processing_failed", extra={"video_id": str(video_id)})
            video = await db.get(Video, video_id)
            if video is not None:
                video.status = "failed"
                await db.commit()


async def process_local_upload(
    video_id: uuid.UUID, user_id: uuid.UUID, content: bytes
) -> None:
    async with SessionLocal() as db:
        video = await db.get(Video, video_id)
        try:
            await _analyze_and_save(db, video, user_id, content)
        except Exception:
            logger.exception("video_processing_failed", extra={"video_id": str(video_id)})
            video = await db.get(Video, video_id)
            if video is not None:
                video.status = "failed"
                await db.commit()


async def process_from_link(
    video_id: uuid.UUID, user_id: uuid.UUID, source_url: str, content_type: str
) -> None:
    async with SessionLocal() as db:
        video = await db.get(Video, video_id)
        try:
            async with httpx.AsyncClient(timeout=LINK_DOWNLOAD_TIMEOUT) as client:
                response = await client.get(source_url, follow_redirects=True)
                response.raise_for_status()
                content = response.content

            video.content_type = content_type
            video.storage_ref = await storage.save(video.id, content, content_type, folder="videos")
            await db.commit()
            await _analyze_and_save(db, video, user_id, content)
        except Exception:
            logger.exception("video_link_processing_failed", extra={"video_id": str(video_id)})
            video = await db.get(Video, video_id)
            if video is not None:
                video.status = "failed"
                await db.commit()


async def list_videos(db: AsyncSession, user_id: uuid.UUID) -> list[Video]:
    # Every published video (any user) + the current user's own drafts —
    # same visibility gate as job_drives.list_job_drives.
    result = await db.scalars(
        select(Video)
        .where(or_(Video.visibility == "published", Video.user_id == user_id))
        .order_by(Video.created_at.desc())
    )
    return list(result)


async def get_video(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID) -> Video:
    video = await db.get(Video, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if video.visibility != "published" and video.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not visible")
    return video


async def get_playback_url(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID) -> str:
    video = await get_video(db, user_id, video_id)
    signed = await storage.presigned_read_url(video.storage_ref)
    # A real signed GCS URL when GCS is configured — the browser plays it
    # straight off GCS, no proxying through this API at all. Otherwise a
    # relative FastAPI path; the frontend BFF proxies that one through
    # itself, since this API requires an auth header a plain <video> tag
    # can't attach (see /library video pages).
    return signed or f"/videos/{video.id}/stream"


async def publish_video(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID) -> Video:
    video = await db.get(Video, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if video.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the creator can publish this")

    video.visibility = "published"
    video.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(video)
    return video


async def record_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    video_id: uuid.UUID,
    event_type: str,
    watch_duration_seconds: float | None,
    completion_pct: float | None,
) -> None:
    db.add(
        VideoEvent(
            user_id=user_id,
            video_id=video_id,
            event_type=event_type,
            watch_duration_seconds=watch_duration_seconds,
            completion_pct=completion_pct,
        )
    )
    await db.commit()
