import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CloudConfig(Base):
    __tablename__ = "cloud_configs"
    __table_args__ = {"schema": "cloud_configs"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    storage_ref: Mapped[str] = mapped_column(String(500))
    resource_count: Mapped[int] = mapped_column(Integer)
    # [{"type": "google_storage_bucket", "count": 1}, ...] — captured once at
    # upload time, same reasoning as Dataset.columns in phase 11: lets
    # list_cloud_configs answer "what's uploaded and roughly what's in it"
    # from the DB alone, no re-parse needed just to list what exists.
    resource_types: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
