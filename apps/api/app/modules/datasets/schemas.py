import uuid
from datetime import datetime

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    dtype: str


class DatasetRead(BaseModel):
    id: uuid.UUID
    title: str
    row_count: int
    columns: list[ColumnInfo]
    created_at: datetime

    model_config = {"from_attributes": True}
