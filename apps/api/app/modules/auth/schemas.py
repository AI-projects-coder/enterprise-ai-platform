import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr

Profession = Literal["student", "job_seeker", "it_professional"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    # Mandatory at signup, not asked again at login — captured once for
    # upcoming role/profession-based features (see User.profession).
    profession: Profession
    # If set, join the inviting org as "member" instead of creating a new
    # org as "owner" — see auth/service.py::register_user.
    invite_token: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    org_id: uuid.UUID
    role: str
    profession: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
