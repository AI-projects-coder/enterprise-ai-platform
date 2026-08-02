from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.video.schemas import VideoRead
from app.modules.video.service import MAX_VIDEO_SIZE, create_video, list_videos, process_video

router = APIRouter(prefix="/videos", tags=["video"])


@router.get("", response_model=list[VideoRead])
async def get_videos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_videos(db, current_user.id)


@router.post("", response_model=VideoRead, status_code=status.HTTP_201_CREATED)
async def upload_video(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_VIDEO_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Video too large ({len(content)} bytes) — max {MAX_VIDEO_SIZE} bytes for now",
        )

    content_type = file.content_type or "video/mp4"
    video = await create_video(db, current_user.id, title, content, content_type)

    # Returns "processing" immediately; analysis (a real Gemini video call,
    # potentially tens of seconds) happens after the response is sent so
    # the upload request itself can't time out waiting on it.
    background_tasks.add_task(process_video, video.id, current_user.id, title, content, content_type)

    return video
