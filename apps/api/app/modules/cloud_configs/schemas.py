import uuid
from datetime import datetime

from pydantic import BaseModel


class ResourceTypeCount(BaseModel):
    type: str
    count: int


class CloudConfigRead(BaseModel):
    id: uuid.UUID
    title: str
    resource_count: int
    resource_types: list[ResourceTypeCount]
    created_at: datetime

    model_config = {"from_attributes": True}
