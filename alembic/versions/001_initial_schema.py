"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column(
            "plan",
            sa.Enum("free", "starter", "growth", "pro", "enterprise", name="userplan"),
            nullable=False,
            server_default="free",
        ),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(100)),
        sa.Column(
            "environment",
            sa.Enum("live", "test", name="keyenvironment"),
            nullable=False,
            server_default="live",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_reset_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    op.create_table(
        "detection_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id")),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_type", sa.Enum("image", "pdf", "video", name="filetype"), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "processing", "completed", "failed", name="jobstatus"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("webhook_url", sa.String(500)),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_msg", sa.Text()),
    )
    op.create_index("ix_detection_jobs_user_id", "detection_jobs", ["user_id"])
    op.create_index("ix_detection_jobs_status", "detection_jobs", ["status"])

    op.create_table(
        "detection_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("detection_jobs.id"), nullable=False, unique=True),
        sa.Column(
            "overall_verdict",
            sa.Enum("authentic", "tampered", "ai_generated", "inconclusive", name="verdict"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("ela_score", sa.Float()),
        sa.Column("clone_score", sa.Float()),
        sa.Column("metadata_score", sa.Float()),
        sa.Column("ai_gen_score", sa.Float()),
        sa.Column("font_score", sa.Float()),
        sa.Column("ocr_diff_score", sa.Float()),
        sa.Column("heatmap_url", sa.String(500)),
        sa.Column("raw_output", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("detection_jobs.id"), nullable=False),
        sa.Column("stripe_meter_event_id", sa.String(255)),
        sa.Column(
            "hit_type",
            sa.Enum("image_detect", "pdf_detect", "video_detect", name="hittype"),
            nullable=False,
        ),
        sa.Column("billed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("billing_events")
    op.drop_table("detection_results")
    op.drop_index("ix_detection_jobs_status", table_name="detection_jobs")
    op.drop_index("ix_detection_jobs_user_id", table_name="detection_jobs")
    op.drop_table("detection_jobs")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_table("users")
    sa.Enum(name="hittype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="verdict").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="jobstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="filetype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="keyenvironment").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userplan").drop(op.get_bind(), checkfirst=True)
