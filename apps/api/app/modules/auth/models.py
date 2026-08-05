import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Org(Base):
    """Real organizations, replacing the phase-1 stub where org_id was just
    a random UUID with nothing behind it. Every user still belongs to
    exactly one org (created automatically at registration, or joined via
    an enterprise.Invite) — multi-org membership isn't a real need yet, so
    it isn't built."""

    __tablename__ = "orgs"
    __table_args__ = {"schema": "auth"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.orgs.id"), index=True)
    # "owner": created the org (or the sole historical user, backfilled by
    # migration) — can invite members and view org-wide analytics/audit log.
    # "member": joined via an invite.
    role: Mapped[str] = mapped_column(String(20), default="owner")
    # One of "student" / "job_seeker" / "it_professional" — mandatory at
    # signup (see auth/schemas.py's UserCreate), captured for upcoming
    # role/profession-based features. No Python-level default here on
    # purpose: registration should fail loudly if this is ever missing,
    # not silently default it — see the migration for how pre-existing rows
    # were backfilled instead.
    profession: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
