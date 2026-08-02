import uuid
from datetime import datetime

from pydantic import BaseModel


class InviteRead(BaseModel):
    id: uuid.UUID
    token: str
    expires_at: datetime

    model_config = {"from_attributes": True}


class MemberRead(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}
