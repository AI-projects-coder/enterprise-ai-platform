from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import jwt

from app.core.database import get_db
from app.core.logging import user_id_var
from app.core.security import decode_access_token
from app.modules.auth.models import User
from app.modules.auth.schemas import TokenResponse, UserCreate, UserLogin, UserRead
from app.modules.auth.service import authenticate_user, register_user
from app.modules.enterprise.service import consume_invite, record_audit_log, validate_invite

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    user_id_var.set(str(user.id))
    return user


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Coordination lives here, not in auth/service.py — same router-level
    # pattern as ADR 0004/0005: auth doesn't know an invite system exists,
    # enterprise doesn't own user creation, so the router is what connects
    # them for this one request.
    invite = None
    if data.invite_token:
        invite = await validate_invite(db, data.invite_token)

    user = await register_user(
        db, data, org_id=invite.org_id if invite else None, role="member" if invite else "owner"
    )

    if invite:
        await consume_invite(db, invite, user.id)
        await record_audit_log(db, user.org_id, user.id, "member_joined", {"email": user.email})
    else:
        await record_audit_log(db, user.org_id, user.id, "org_created", {"email": user.email})

    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    token = await authenticate_user(db, data)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
