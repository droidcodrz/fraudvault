import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KeyEnvironment(str, enum.Enum):
    live = "live"
    test = "test"


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    environment: Mapped[KeyEnvironment] = mapped_column(
        Enum(KeyEnvironment), default=KeyEnvironment.live, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="api_keys")
    detection_jobs: Mapped[list["DetectionJob"]] = relationship(back_populates="api_key")
    billing_events: Mapped[list["BillingEvent"]] = relationship(back_populates="api_key")


from app.models.user import User  # noqa: E402
from app.models.detection_job import DetectionJob  # noqa: E402
from app.models.billing import BillingEvent  # noqa: E402
