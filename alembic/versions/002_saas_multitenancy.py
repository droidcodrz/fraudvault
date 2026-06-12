"""SaaS multi-tenancy: orgs, plans, auth improvements

Revision ID: 002
Revises: 001
Create Date: 2026-06-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Organizations ───────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("max_members", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Org Memberships ─────────────────────────────────────────────
    orgrole = sa.Enum("owner", "admin", "member", "viewer", name="orgrole")
    orgrole.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "org_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", orgrole, nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_org_memberships_org_id", "org_memberships", ["org_id"])
    op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])
    op.create_unique_constraint("uq_org_memberships_org_user", "org_memberships", ["org_id", "user_id"])

    # ── Org Invites ─────────────────────────────────────────────────
    invitestatus = sa.Enum("pending", "accepted", "expired", "revoked", name="invitestatus")
    invitestatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "org_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", orgrole, nullable=False, server_default="member"),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("status", invitestatus, nullable=False, server_default="pending"),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Plans ───────────────────────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("monthly_price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("annual_price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_detection_limit", sa.Integer()),
        sa.Column("rate_limit_per_minute", sa.Integer()),
        sa.Column("rate_limit_per_day", sa.Integer()),
        sa.Column("max_file_size_mb", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("max_members", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_api_keys", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("features", sa.Text()),
        sa.Column("stripe_monthly_price_id", sa.String(255)),
        sa.Column("stripe_annual_price_id", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Password Resets ─────────────────────────────────────────────
    op.create_table(
        "password_resets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Email Verifications ─────────────────────────────────────────
    op.create_table(
        "email_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── User table additions ────────────────────────────────────────
    userrole = sa.Enum("user", "admin", name="userrole")
    userrole.create(op.get_bind(), checkfirst=True)

    op.add_column("users", sa.Column("role", userrole, nullable=False, server_default="user"))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column(
        "current_org_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("organizations.id", ondelete="SET NULL", use_alter=True),
    ))

    # ── Tenant scoping: org_id on api_keys and detection_jobs ──────
    op.add_column("api_keys", sa.Column(
        "org_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("organizations.id", ondelete="SET NULL"),
    ))
    op.add_column("detection_jobs", sa.Column(
        "org_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("organizations.id", ondelete="SET NULL"),
    ))
    op.create_index("ix_detection_jobs_org_id", "detection_jobs", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_detection_jobs_org_id", table_name="detection_jobs")
    op.drop_column("detection_jobs", "org_id")
    op.drop_column("api_keys", "org_id")
    op.drop_column("users", "current_org_id")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "role")

    op.drop_table("email_verifications")
    op.drop_table("password_resets")
    op.drop_table("plans")
    op.drop_table("org_invites")
    op.drop_index("ix_org_memberships_user_id", table_name="org_memberships")
    op.drop_index("ix_org_memberships_org_id", table_name="org_memberships")
    op.drop_table("org_memberships")
    op.drop_table("organizations")

    sa.Enum(name="invitestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="orgrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
