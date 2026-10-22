"""system_resources + system_aliases; drop invitations (single-administrator model)

Revision ID: 5b2e9a1c7d40
Revises: 14e9fcd6dc8d
Create Date: 2026-10-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "5b2e9a1c7d40"
down_revision = "14e9fcd6dc8d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_resources",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("system_key", sa.String(300), nullable=False),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("design_systems.id", ondelete="SET NULL")),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("label", sa.String(300)),
        sa.Column("origin", sa.String(30), nullable=False),
        sa.Column("source_keys", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="unverified"),
        sa.Column("verification_method", sa.String(80)),
        sa.Column("evidence_url", sa.Text()),
        sa.Column("evidence_note", sa.Text()),
        sa.Column("http_status", sa.Integer()),
        sa.Column("access_note", sa.Text()),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("system_key", "resource_type", "canonical_url", name="uq_system_resource"),
    )
    for c in ("system_key", "system_id", "resource_type", "verification_status"):
        op.create_index(f"ix_system_resources_{c}", "system_resources", [c])
    op.create_table(
        "system_aliases",
        sa.Column("alias_key", sa.String(300), primary_key=True),
        sa.Column("alias_id", sa.Integer()),
        sa.Column("alias_name", sa.String(300)),
        sa.Column("canonical_key", sa.String(300), nullable=False),
        sa.Column("reason", sa.String(60), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_system_aliases_alias_id", "system_aliases", ["alias_id"])
    op.create_index("ix_system_aliases_canonical_key", "system_aliases", ["canonical_key"])
    # Single-administrator model: invitation-based onboarding is removed (rows were test invitations; see backups/).
    op.drop_table("invitations")


def downgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(10), nullable=False, server_default="access"),
        sa.Column("email", sa.String(320), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("accepted_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("delivery_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("delivery_error", sa.Text()),
        sa.Column("send_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sent_at", sa.DateTime(timezone=True)),
        sa.Column("code_digest", sa.String(64)),
        sa.Column("code_expires_at", sa.DateTime(timezone=True)),
        sa.Column("code_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("code_sent_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_table("system_aliases")
    op.drop_table("system_resources")
