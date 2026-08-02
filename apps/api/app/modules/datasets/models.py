import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = {"schema": "datasets"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    storage_ref: Mapped[str] = mapped_column(String(500))
    row_count: Mapped[int] = mapped_column(Integer)
    # [{"name": "revenue", "dtype": "float64"}, ...] — captured once at
    # upload time so the agent's list_datasets tool can see each dataset's
    # shape without re-downloading and re-parsing the file just to answer
    # "what datasets do I have and what columns do they have".
    columns: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
