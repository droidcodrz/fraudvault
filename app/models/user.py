import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserPlan(str, enum.Enum):
    free = "free"
    starter = "starter"
    growth = "growth"
    pro = "pro"
    enterprise = "enterprise"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[UserPlan] = mapped_column(Enum(UserPlan), default=UserPlan.free, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    detection_jobs: Mapped[list["DetectionJob"]] = relationship(back_populates="user")
    billing_events: Mapped[list["BillingEvent"]] = relationship(back_populates="user")


from app.models.api_key import APIKey  # noqa: E402
from app.models.detection_job import DetectionJob  # noqa: E402
from app.models.billing import BillingEvent  # noqa: E402
