import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.job_drives.schemas import JobDriveCreate, JobDriveRead
from app.modules.job_drives.service import create_job_drive, list_job_drives, publish_job_drive

router = APIRouter(prefix="/job-drives", tags=["job-drives"])


@router.get("", response_model=list[JobDriveRead])
async def get_job_drives(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_job_drives(db, current_user.id)


@router.post("", response_model=JobDriveRead, status_code=201)
async def post_job_drive(
    data: JobDriveCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_job_drive(db, current_user.id, data.role, data.city, data.experience_band)


@router.patch("/{drive_id}/publish", response_model=JobDriveRead)
async def publish(
    drive_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await publish_job_drive(db, current_user.id, drive_id)
