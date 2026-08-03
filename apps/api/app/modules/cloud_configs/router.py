from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.cloud_configs.schemas import CloudConfigRead
from app.modules.cloud_configs.service import MAX_CONFIG_SIZE, create_cloud_config, list_cloud_configs

router = APIRouter(prefix="/cloud-configs", tags=["cloud-configs"])


@router.get("", response_model=list[CloudConfigRead])
async def get_cloud_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_cloud_configs(db, current_user.id)


@router.post("", response_model=CloudConfigRead, status_code=status.HTTP_201_CREATED)
async def upload_cloud_config(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_CONFIG_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File too large ({len(content)} bytes) — max {MAX_CONFIG_SIZE} bytes for now",
        )

    # Parsed synchronously inside create_cloud_config — a malformed .tf file
    # is rejected right here with a clear error, same as datasets' CSV parsing.
    return await create_cloud_config(db, current_user.id, title, content)
