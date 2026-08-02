import uuid
from datetime import datetime

from pydantic import BaseModel


class VideoRead(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
