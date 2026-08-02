import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    title: str
    content: str


class DocumentRead(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}
