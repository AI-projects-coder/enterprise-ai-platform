import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import SessionLocal
from app.modules.ai_gateway.service import analyze_video
from app.modules.knowledge.service import ingest_document
from app.modules.video.models import Video

logger = logging.getLogger("app.video")

# Keeps inline Gemini video requests and single-request background
# processing time bounded for v1 — a real production version would chunk
# larger uploads through Gemini's Files API and process via a real job
# queue instead of FastAPI's BackgroundTasks.
MAX_VIDEO_SIZE = 20 * 1024 * 1024


async def create_video(
    db: AsyncSession, user_id: uuid.UUID, title: str, content: bytes, content_type: str
) -> Video:
    video = Video(user_id=user_id, title=title, storage_ref="", status="processing")
    db.add(video)
    await db.flush()  # assigns video.id before it's needed as the storage key

    video.storage_ref = await storage.save(video.id, content, content_type)
    await db.commit()
    await db.refresh(video)
    return video


async def process_video(
    video_id: uuid.UUID, user_id: uuid.UUID, title: str, content: bytes, content_type: str
) -> None:
    """Runs via FastAPI BackgroundTasks, after the upload response has
    already been sent — so it needs its OWN db session (the request's
    session is closed by then), created directly from SessionLocal rather
    than the get_db dependency, which only exists for the request lifecycle."""
    async with SessionLocal() as db:
        try:
            transcript = await analyze_video(content, content_type)
            document = await ingest_document(db, user_id, title, transcript)

            video = await db.get(Video, video_id)
            video.document_id = document.id
            video.status = "ready"
            await db.commit()
        except Exception:
            logger.exception("video_processing_failed", extra={"video_id": str(video_id)})
            video = await db.get(Video, video_id)
            if video is not None:
                video.status = "failed"
                await db.commit()


async def list_videos(db: AsyncSession, user_id: uuid.UUID) -> list[Video]:
    result = await db.scalars(
        select(Video).where(Video.user_id == user_id).order_by(Video.created_at.desc())
    )
    return list(result)
