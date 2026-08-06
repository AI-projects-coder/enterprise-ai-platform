import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobDriveCreate(BaseModel):
    role: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    experience_band: str = Field(min_length=1, max_length=20)


class JobDriveRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    city: str
    experience_band: str
    generated_content: str
    status: str
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
