import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.video.schemas import (
    FromLinkRequest,
    PlaybackUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
    VideoDetail,
    VideoEventCreate,
    VideoRead,
)
from app.modules.video.service import (
    MAX_VIDEO_SIZE,
    confirm_upload,
    create_from_link,
    create_local_upload,
    create_upload_target,
    get_playback_url,
    get_video,
    list_videos,
    process_from_link,
    process_local_upload,
    process_upload,
    publish_video,
    record_event,
)

router = APIRouter(prefix="/videos", tags=["video"])


@router.get("", response_model=list[VideoRead])
async def get_videos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_videos(db, current_user.id)


@router.get("/{video_id}", response_model=VideoDetail)
async def get_video_detail(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video = await get_video(db, current_user.id, video_id)
    playback_url = await get_playback_url(db, current_user.id, video_id)
    return VideoDetail(
        **VideoRead.model_validate(video).model_dump(),
        transcript_segments=video.transcript_segments,
        summary_notes=video.summary_notes,
        key_points=video.key_points,
        quiz=video.quiz,
        playback_url=playback_url,
    )


@router.post("/upload-url", response_model=UploadUrlResponse)
async def post_upload_url(
    body: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # No longer unconditionally 201 — a row is only actually created when
    # GCS is configured (see create_upload_target's docstring).
    video, upload_url = await create_upload_target(
        db, current_user.id, body.title, body.description, body.content_type
    )
    return UploadUrlResponse(video_id=video.id if video else None, upload_url=upload_url)


@router.post("/{video_id}/confirm-upload", response_model=VideoRead)
async def post_confirm_upload(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video = await confirm_upload(db, current_user.id, video_id)
    background_tasks.add_task(process_upload, video.id, current_user.id)
    return video


@router.post("/local-upload", response_model=VideoRead, status_code=status.HTTP_201_CREATED)
async def post_local_upload(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Local-dev-only fallback used when storage.presigned_upload_url
    returned None (no GCS_BUCKET configured) — the frontend detects this
    from POST /videos/upload-url's response and calls here instead."""
    content = await file.read()
    if len(content) > MAX_VIDEO_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Video too large ({len(content)} bytes) — max {MAX_VIDEO_SIZE} bytes for now",
        )

    content_type = file.content_type or "video/mp4"
    video = await create_local_upload(db, current_user.id, title, description, content, content_type)
    background_tasks.add_task(process_local_upload, video.id, current_user.id, content)
    return video


@router.post("/from-link", response_model=VideoRead, status_code=status.HTTP_201_CREATED)
async def post_from_link(
    body: FromLinkRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video = await create_from_link(db, current_user.id, body.title, body.description, body.source_url)
    background_tasks.add_task(
        process_from_link, video.id, current_user.id, body.source_url, "video/mp4"
    )
    return video


@router.patch("/{video_id}/publish", response_model=VideoRead)
async def patch_publish(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await publish_video(db, current_user.id, video_id)


@router.get("/{video_id}/stream")
async def get_stream(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Local-disk-only playback path — get_playback_url only ever returns
    this URL when there's no GCS bucket to sign a real URL against, so
    storage_ref here is always a local filesystem path, never gs://."""
    video = await get_video(db, current_user.id, video_id)
    content = await storage.load(video.storage_ref)
    return Response(content=content, media_type=video.content_type)


@router.post("/{video_id}/events", status_code=status.HTTP_204_NO_CONTENT)
async def post_event(
    video_id: uuid.UUID,
    body: VideoEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await record_event(
        db, current_user.id, video_id, body.event_type, body.watch_duration_seconds, body.completion_pct
    )
