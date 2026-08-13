import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.support.schemas import (
    AttachmentUploadUrlRequest,
    AttachmentUploadUrlResponse,
    TicketAttachmentRead,
    TicketCreate,
    TicketDetail,
    TicketRead,
)
from app.modules.support.service import (
    confirm_attachment_upload,
    create_attachment_upload_target,
    create_local_attachment,
    create_ticket,
    get_ticket,
    get_ticket_detail,
    list_tickets,
    process_ticket_submission,
)

from app.modules.support.schemas import SimilarityCheckRequest   # add to the existing import
from app.modules.support.service import find_similar_tickets     # add to the existing import


router = APIRouter(prefix="/tickets", tags=["support"])

@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def post_ticket(
    body: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_ticket(db, current_user.id, body.description)


@router.post("/{ticket_id}/attachments/upload-url", response_model=AttachmentUploadUrlResponse)
async def post_attachment_upload_url(
    ticket_id: uuid.UUID,
    body: AttachmentUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attachment, upload_url = await create_attachment_upload_target(
        db, current_user.id, ticket_id, body.content_type
    )
    return AttachmentUploadUrlResponse(
        attachment_id=attachment.id if attachment else None, upload_url=upload_url
    )
    
    
    
    
@router.post(
    "/{ticket_id}/attachments/{attachment_id}/confirm-upload", response_model=TicketAttachmentRead
)
async def post_confirm_attachment_upload(
    ticket_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await confirm_attachment_upload(db, current_user.id, ticket_id, attachment_id)

@router.post(
    "/{ticket_id}/attachments/local-upload",
    response_model=TicketAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_local_attachment(
    ticket_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    return await create_local_attachment(db, current_user.id, ticket_id, content, content_type)



@router.post("/similar", response_model=list[TicketRead])
async def post_similar_tickets(
    body: SimilarityCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await find_similar_tickets(db, body.description)


@router.get("", response_model=list[TicketRead])
async def get_tickets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_tickets(db, current_user.id)

async def _attachment_view_url(attachment) -> str:
    signed = await storage.presigned_read_url(attachment.storage_ref)
    # Real signed GCS URL when GCS is configured — browser loads it
    # directly. Otherwise a relative FastAPI path; the frontend BFF proxies
    # that one through itself, same reasoning as video's playback_url.
    return signed or f"/tickets/{attachment.ticket_id}/attachments/{attachment.id}/stream"


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket_detail_endpoint(
    ticket_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket, attachments = await get_ticket_detail(db, current_user.id, ticket_id)
    attachment_reads = [
        TicketAttachmentRead(
            id=a.id,
            storage_ref=a.storage_ref,
            content_type=a.content_type,
            view_url=await _attachment_view_url(a),
        )
        for a in attachments
    ]
    return TicketDetail(
        **TicketRead.model_validate(ticket).model_dump(),
        attachments=attachment_reads,
    )


@router.get("/{ticket_id}/attachments/{attachment_id}/stream")
async def get_attachment_stream(
    ticket_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Local-disk-only playback path — _attachment_view_url only ever
    returns this URL when there's no GCS bucket to sign a real URL
    against, same reasoning as video's /videos/{id}/stream."""
    _, attachments = await get_ticket_detail(db, current_user.id, ticket_id)
    attachment = next((a for a in attachments if a.id == attachment_id), None)
    if attachment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    content = await storage.load(attachment.storage_ref)
    return Response(content=content, media_type=attachment.content_type)
    
@router.post("/{ticket_id}/submit", response_model=TicketRead)
async def post_submit_ticket(
    ticket_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await get_ticket(db, current_user.id, ticket_id)
    background_tasks.add_task(process_ticket_submission, ticket_id)
    return ticket