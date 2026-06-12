import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FileType(str, enum.Enum):
    image = "image"
    pdf = "pdf"
    video = "video"


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DetectionJob(Base):
    __tablename__ = "detection_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[FileType] = mapped_column(Enum(FileType), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.queued, nullable=False, index=True
    )
    webhook_url: Mapped[str | None] = mapped_column(String(500))
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_msg: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="detection_jobs")
    api_key: Mapped["APIKey | None"] = relationship(back_populates="detection_jobs")
    result: Mapped["DetectionResult | None"] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    billing_events: Mapped[list["BillingEvent"]] = relationship(back_populates="job")


from app.models.user import User  # noqa: E402
from app.models.api_key import APIKey  # noqa: E402
from app.models.detection_result import DetectionResult  # noqa: E402
from app.models.billing import BillingEvent  # noqa: E402
