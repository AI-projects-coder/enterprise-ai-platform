from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.analytics.schemas import OrgUsageSummary, UsageSummary
from app.modules.analytics.service import get_org_usage_summary, get_usage_summary
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.enterprise.router import require_owner

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/me", response_model=UsageSummary)
async def my_usage(
    since_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_usage_summary(db, current_user.id, since_days)


@router.get("/org", response_model=OrgUsageSummary)
async def org_usage(
    since_days: int = 30,
    current_user: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    return await get_org_usage_summary(db, current_user.org_id, since_days)
