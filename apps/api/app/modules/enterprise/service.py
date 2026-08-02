import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.enterprise.models import AuditLog, Invite

INVITE_EXPIRY = timedelta(days=7)


async def create_invite(db: AsyncSession, org_id: uuid.UUID, created_by: uuid.UUID) -> Invite:
    invite = Invite(
        org_id=org_id,
        token=secrets.token_urlsafe(24),
        created_by=created_by,
        expires_at=datetime.now(timezone.utc) + INVITE_EXPIRY,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


async def validate_invite(db: AsyncSession, token: str) -> Invite:
    """Read-only check — does NOT mark the invite used. Registration can
    still fail after this (e.g. duplicate email), and an invite shouldn't
    be burned for a registration attempt that never actually succeeded."""
    invite = await db.scalar(select(Invite).where(Invite.token == token))
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid invite link")
    if invite.used_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This invite has already been used")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_410_GONE, "This invite has expired")
    return invite


async def consume_invite(db: AsyncSession, invite: Invite, used_by: uuid.UUID) -> None:
    invite.used_at = datetime.now(timezone.utc)
    invite.used_by = used_by
    await db.commit()


async def record_audit_log(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    details: dict | None = None,
) -> None:
    db.add(AuditLog(org_id=org_id, user_id=user_id, action=action, details=details or {}))
    await db.commit()


async def get_org_members(db: AsyncSession, org_id: uuid.UUID) -> list[User]:
    result = await db.scalars(select(User).where(User.org_id == org_id).order_by(User.created_at))
    return list(result)


async def get_audit_log(db: AsyncSession, org_id: uuid.UUID, limit: int = 100) -> list[AuditLog]:
    result = await db.scalars(
        select(AuditLog).where(AuditLog.org_id == org_id).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    return list(result)
