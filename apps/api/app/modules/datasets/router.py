from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.datasets.schemas import DatasetRead
from app.modules.datasets.service import MAX_DATASET_SIZE, create_dataset, list_datasets

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetRead])
async def get_datasets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_datasets(db, current_user.id)


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_DATASET_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Dataset too large ({len(content)} bytes) — max {MAX_DATASET_SIZE} bytes for now",
        )

    # Parsed synchronously inside create_dataset — a malformed CSV is
    # rejected right here with a clear error, not discovered later mid-chat
    # the way a failed async video analysis would be.
    return await create_dataset(db, current_user.id, title, content)
