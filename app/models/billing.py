import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HitType(str, enum.Enum):
    image_detect = "image_detect"
    pdf_detect = "pdf_detect"
    video_detect = "video_detect"


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_jobs.id"), nullable=False
    )
    stripe_meter_event_id: Mapped[str | None] = mapped_column(String(255))
    hit_type: Mapped[HitType] = mapped_column(Enum(HitType), nullable=False)
    billed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="billing_events")
    api_key: Mapped["APIKey | None"] = relationship(back_populates="billing_events")
    job: Mapped["DetectionJob"] = relationship(back_populates="billing_events")


from app.models.user import User  # noqa: E402
from app.models.api_key import APIKey  # noqa: E402
from app.models.detection_job import DetectionJob  # noqa: E402
