from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.enterprise.schemas import AuditLogRead, InviteRead, MemberRead
from app.modules.enterprise.service import create_invite, get_audit_log, get_org_members

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


def require_owner(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the org owner can do this")
    return current_user


@router.post("/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
async def invite_member(
    current_user: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    return await create_invite(db, current_user.org_id, current_user.id)


@router.get("/members", response_model=list[MemberRead])
async def list_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_org_members(db, current_user.org_id)


@router.get("/audit-log", response_model=list[AuditLogRead])
async def audit_log(
    current_user: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    return await get_audit_log(db, current_user.org_id)
