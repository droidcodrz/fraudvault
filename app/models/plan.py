import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    monthly_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    annual_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    monthly_detection_limit: Mapped[int | None] = mapped_column(Integer)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer)
    rate_limit_per_day: Mapped[int | None] = mapped_column(Integer)
    max_file_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    max_members: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    max_api_keys: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    features: Mapped[str | None] = mapped_column(Text)
    stripe_monthly_price_id: Mapped[str | None] = mapped_column(String(255))
    stripe_annual_price_id: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
