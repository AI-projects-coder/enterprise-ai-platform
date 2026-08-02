import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = {"schema": "enterprise"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.orgs.id"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    used_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth.users.id"), default=None)


class AuditLog(Base):
    """Security/membership-relevant events an enterprise buyer would expect
    a record of — who did what, when. Deliberately minimal set of actions
    for now (org_created, invite_created, member_joined); extend as real
    enterprise-tier actions (role changes, billing, SSO config) get built."""

    __tablename__ = "audit_log"
    __table_args__ = {"schema": "enterprise"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.orgs.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth.users.id"), default=None)
    action: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
