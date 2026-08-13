import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base  
from app.modules.knowledge.models import EMBEDDING_DIM


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {"schema": "support"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    description_embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), default=None)
    priority: Mapped[str | None] = mapped_column(String(20), default=None)
    # "open" -> "in_progress" -> "resolved" — drives which tab a ticket
    # shows up in on the frontend.
    status: Mapped[str] = mapped_column(String(20), default="open")
    jira_issue_key: Mapped[str | None] = mapped_column(String(50), default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    __table_args__ = {"schema": "support"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support.tickets.id"), nullable=False)
    storage_ref: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    
    

