import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.models import Org, User
from app.modules.auth.schemas import UserCreate, UserLogin


async def register_user(
    db: AsyncSession, data: UserCreate, org_id: uuid.UUID | None = None, role: str = "owner"
) -> User:
    """org_id/role are decided by the caller (auth/router.py), not here —
    this module has no idea an invite system exists. Pass org_id=None to
    create a brand new org (the normal signup path); pass an existing
    org_id (from a validated invite) to join it as "member" instead."""
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    if org_id is None:
        org = Org(name=f"{data.email}'s Organization")
        db.add(org)
        await db.flush()  # assigns org.id without committing, same pattern as knowledge's document/chunk flush
        org_id = org.id
        role = "owner"

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        org_id=org_id,
        role=role,
        profession=data.profession,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, data: UserLogin) -> str:
    user = await db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return create_access_token(subject=str(user.id))
