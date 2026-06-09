import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Verdict(str, enum.Enum):
    authentic = "authentic"
    tampered = "tampered"
    ai_generated = "ai_generated"
    inconclusive = "inconclusive"


class DetectionResult(Base):
    __tablename__ = "detection_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_jobs.id"), unique=True, nullable=False
    )
    overall_verdict: Mapped[Verdict] = mapped_column(Enum(Verdict), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    flags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    ela_score: Mapped[float | None] = mapped_column(Float)
    clone_score: Mapped[float | None] = mapped_column(Float)
    metadata_score: Mapped[float | None] = mapped_column(Float)
    ai_gen_score: Mapped[float | None] = mapped_column(Float)
    font_score: Mapped[float | None] = mapped_column(Float)
    ocr_diff_score: Mapped[float | None] = mapped_column(Float)
    heatmap_url: Mapped[str | None] = mapped_column(String(500))
    raw_output: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["DetectionJob"] = relationship(back_populates="result")


from app.models.detection_job import DetectionJob  # noqa: E402
