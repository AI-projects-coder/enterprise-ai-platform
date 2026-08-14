import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.modules.support.models import Ticket, TicketAttachment
from app.modules.ai_gateway.service import embed
from sqlalchemy import select   # add to the existing sqlalchemy import
from app.modules.ai_gateway.service import TicketClassification, classify_ticket_priority
from app.modules.support.jira import attach_files_to_issue, create_jira_issue
import mimetypes
import logging

from app.core.database import SessionLocal
from app.modules.auth.models import User
from datetime import datetime, timezone
from app.modules.support.jira import get_jira_issue_status
from app.modules.support.email import send_ticket_raised_email, send_ticket_resolved_email



logger = logging.getLogger("app.support")

# Local-dev-only fallback cap — same reasoning as MAX_VIDEO_SIZE.
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024
SIMILARITY_TOP_K = 3
SIMILARITY_THRESHOLD = 0.3


async def create_ticket(db: AsyncSession, user_id: uuid.UUID, description: str) -> Ticket:
    embedding = await embed(description)
    ticket = Ticket(user_id=user_id, description=description, description_embedding=embedding)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket

async def get_ticket(db: AsyncSession, user_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None or ticket.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return ticket


async def create_attachment_upload_target(
    db: AsyncSession, user_id: uuid.UUID, ticket_id: uuid.UUID, content_type: str
) -> tuple[TicketAttachment | None, str | None]:
    """Same shape as video's create_upload_target, and for the same reason:
    flush (not commit) BEFORE the signing call, commit only after it
    succeeds — so a signing failure never leaves an orphaned attachment row
    behind, the exact bug we hit and fixed for video uploads."""
    await get_ticket(db, user_id, ticket_id)  # 404s if this isn't your ticket

    if not storage.GCS_BUCKET:
        return None, None

    attachment = TicketAttachment(ticket_id=ticket_id, storage_ref="", content_type=content_type)
    db.add(attachment)
    await db.flush()

    upload_url = await storage.presigned_upload_url(attachment.id, content_type, folder="support")

    await db.commit()
    await db.refresh(attachment)
    return attachment, upload_url

async def confirm_attachment_upload(
    db: AsyncSession, user_id: uuid.UUID, ticket_id: uuid.UUID, attachment_id: uuid.UUID
) -> TicketAttachment:
    await get_ticket(db, user_id, ticket_id)

    attachment = await db.get(TicketAttachment, attachment_id)
    if attachment is None or attachment.ticket_id != ticket_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")

    attachment.storage_ref = f"gs://{storage.GCS_BUCKET}/support/{attachment.id}"
    await db.commit()
    await db.refresh(attachment)
    return attachment


async def create_local_attachment(
    db: AsyncSession, user_id: uuid.UUID, ticket_id: uuid.UUID, content: bytes, content_type: str
) -> TicketAttachment:
    """Local-dev-only fallback — same reasoning as create_local_upload."""
    await get_ticket(db, user_id, ticket_id)

    if len(content) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File too large ({len(content)} bytes) — max {MAX_ATTACHMENT_SIZE} bytes for local dev",
        )

    attachment = TicketAttachment(ticket_id=ticket_id, storage_ref="", content_type=content_type)
    db.add(attachment)
    await db.flush()

    attachment.storage_ref = await storage.save(attachment.id, content, content_type, folder="support")
    await db.commit()
    await db.refresh(attachment)
    return attachment



async def find_similar_tickets(db: AsyncSession, description: str) -> list[Ticket]:
    query_vector = await embed(description)

    result = await db.scalars(
        select(Ticket)
        .where(Ticket.description_embedding.is_not(None))
        .where(Ticket.description_embedding.cosine_distance(query_vector) < SIMILARITY_THRESHOLD)
        .order_by(Ticket.description_embedding.cosine_distance(query_vector))
        .limit(SIMILARITY_TOP_K)
    )
    return list(result)




async def classify_and_update_ticket(
    db: AsyncSession, ticket: Ticket, attachments: list[TicketAttachment]
) -> TicketClassification:
    """Loads each attachment's bytes back from storage — same shape as
    video's process_upload loading bytes before its own Gemini call.
    Persists `priority` on the ticket. The short `summary` title is
    deliberately NOT stored anywhere — it only exists to feed straight into
    Jira issue creation (Step 6), which runs immediately after this, so
    there's no reason to round-trip it through the database first."""
    loaded = [(await storage.load(a.storage_ref), a.content_type) for a in attachments]
    classification = await classify_ticket_priority(ticket.description, loaded)

    ticket.priority = classification.priority
    await db.commit()
    return classification


async def create_and_link_jira_issue(
    db: AsyncSession,
    ticket: Ticket,
    classification: TicketClassification,
    attachments: list[TicketAttachment],
    reporter_email: str,
) -> None:
    issue_key = await create_jira_issue(
        classification.summary, ticket.description, classification.priority, reporter_email
    )
    if issue_key:
        ticket.jira_issue_key = issue_key
        await db.commit()

        # Issue must exist first — attaching files is a separate call
        # against an issue key that only exists after creation succeeds.
        files = [
            (_attachment_filename(a), await storage.load(a.storage_ref), a.content_type)
            for a in attachments
        ]
        await attach_files_to_issue(issue_key, files)


def _attachment_filename(attachment: TicketAttachment) -> str:
    extension = mimetypes.guess_extension(attachment.content_type) or ""
    return f"attachment-{attachment.id}{extension}"
        
async def list_tickets(db: AsyncSession, user_id: uuid.UUID) -> list[Ticket]:
    result = await db.scalars(
        select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())
    )
    return list(result)


async def get_ticket_detail(
    db: AsyncSession, user_id: uuid.UUID, ticket_id: uuid.UUID
) -> tuple[Ticket, list[TicketAttachment]]:
    ticket = await get_ticket(db, user_id, ticket_id)
    attachments = list(
        await db.scalars(select(TicketAttachment).where(TicketAttachment.ticket_id == ticket_id))
    )
    return ticket, attachments

async def process_ticket_submission(ticket_id: uuid.UUID) -> None:
    """Runs via FastAPI BackgroundTasks after POST /tickets/{id}/submit
    already returned — needs its own db session, same reasoning as video's
    process_upload (the request's session is closed by the time this runs)."""
    async with SessionLocal() as db:
        ticket = await db.get(Ticket, ticket_id)
        user = await db.get(User, ticket.user_id)
        attachments = list(
            await db.scalars(select(TicketAttachment).where(TicketAttachment.ticket_id == ticket_id))
        )

        await send_ticket_raised_email(user.email, str(ticket.id))

        try:
            classification = await classify_and_update_ticket(db, ticket, attachments)
            await create_and_link_jira_issue(db, ticket, classification, attachments, user.email)
            ticket.status = "in_progress"
            await db.commit()
        except Exception:
            logger.exception("ticket_submission_pipeline_failed", extra={"ticket_id": str(ticket_id)})
            
            
async def sync_ticket_statuses(db: AsyncSession) -> int:
    """Polls Jira for every ticket we're still tracking (has a jira_issue_key,
    not yet resolved) and updates our own status when Jira reports it done.
    Returns how many tickets were newly resolved, purely for the job's own
    log line. Runs as a scheduled Cloud Run Job, never from an HTTP request."""
    tickets = list(
        await db.scalars(
            select(Ticket).where(Ticket.jira_issue_key.is_not(None), Ticket.status != "resolved")
        )
    )

    resolved_count = 0
    for ticket in tickets:
        status_category = await get_jira_issue_status(ticket.jira_issue_key)
        if status_category == "done":
            ticket.status = "resolved"
            ticket.resolved_at = datetime.now(timezone.utc)
            await db.commit()

            user = await db.get(User, ticket.user_id)
            await send_ticket_resolved_email(user.email, str(ticket.id))
            resolved_count += 1

    return resolved_count