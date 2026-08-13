import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel,Field

Priority = Literal["low", "medium", "high", "highest"]
TicketStatus = Literal["open", "in_progress", "resolved"]

class TicketAttachmentRead(BaseModel):
    id: uuid.UUID
    storage_ref: str
    content_type: str
    # A real signed GCS URL when GCS is configured, or a relative FastAPI
    # path the frontend proxies through itself when it's not — same
    # playback_url pattern VideoDetail already uses.
    view_url: str
    model_config = {"from_attributes": True}
    


class TicketRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    description: str
    priority: Priority | None
    status: TicketStatus
    jira_issue_key: str | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
    
class TicketDetail(TicketRead):
    attachments: list[TicketAttachmentRead]

class TicketCreate(BaseModel):
    description: str = Field(min_length=1)
    
class AttachmentUploadUrlRequest(BaseModel):
    content_type: str
    
class AttachmentUploadUrlResponse(BaseModel):
    # Both None together when GCS isn't configured (local dev) — same
    # meaning as video's UploadUrlResponse.
    attachment_id: uuid.UUID | None
    upload_url: str | None

class SimilarityCheckRequest(BaseModel):
    description: str = Field(min_length=1)
    