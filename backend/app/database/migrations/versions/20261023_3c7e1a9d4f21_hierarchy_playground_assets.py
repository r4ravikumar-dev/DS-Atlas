"""System hierarchy: stable slugs, token categories/tiers, the component-family taxonomy, and system visual assets.

Additive only. Slugs, token categories and the family taxonomy are filled by `services/catalog.refresh` (run after every
build and once via `manage.py refresh-catalog`); existing slugs are never rewritten, so URLs stay stable.

Revision ID: 3c7e1a9d4f21
Revises: 8d1f3a6b2c90
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "3c7e1a9d4f21"
down_revision = "8d1f3a6b2c90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("design_systems", sa.Column("slug", sa.String(120)))
    op.create_index("uq_design_systems_slug", "design_systems", ["slug"], unique=True)

    op.add_column("components", sa.Column("slug", sa.String(160)))
    op.create_index("uq_components_system_slug", "components", ["system_id", "slug"], unique=True)

    op.add_column("design_tokens", sa.Column("slug", sa.String(220)))
    op.add_column("design_tokens", sa.Column("category", sa.String(30)))
    op.add_column("design_tokens", sa.Column("tier", sa.String(20)))
    op.create_index("uq_design_tokens_system_slug", "design_tokens", ["system_id", "slug"], unique=True)
    op.create_index("ix_design_tokens_system_category", "design_tokens", ["system_id", "category"])

    op.add_column("guidelines", sa.Column("slug", sa.String(220)))
    op.create_index("uq_guidelines_system_slug", "guidelines", ["system_id", "slug"], unique=True)

    op.create_table(
        "component_families",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("category", sa.String(60), nullable=False, index=True),
        sa.Column("description", sa.Text),
        sa.Column("aliases", JSONB, nullable=False, server_default="[]"),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "system_assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("system_id", sa.Integer, sa.ForeignKey("design_systems.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", sa.String(30), nullable=False),  # icon | social_image | organization_avatar
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("page_url", sa.Text),  # where the asset was found (provenance)
        sa.Column("source_host", sa.String(300)),
        sa.Column("source_organization", sa.String(300)),
        sa.Column("alt", sa.String(400)),
        sa.Column("mime", sa.String(100)),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("bytes", sa.Integer),
        sa.Column("content_sha256", sa.String(64)),
        sa.Column("attribution", sa.Text),
        sa.Column("license", sa.Text),  # never guessed: null means "not stated by the source"
        sa.Column("status", sa.String(20), nullable=False, server_default="ok"),  # ok | broken | blocked
        sa.Column("error", sa.Text),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("system_id", "kind", "url", name="uq_system_assets_system_kind_url"),
    )


def downgrade() -> None:
    op.drop_table("system_assets")
    op.drop_table("component_families")
    op.drop_index("uq_guidelines_system_slug", table_name="guidelines")
    op.drop_column("guidelines", "slug")
    op.drop_index("ix_design_tokens_system_category", table_name="design_tokens")
    op.drop_index("uq_design_tokens_system_slug", table_name="design_tokens")
    for c in ("tier", "category", "slug"):
        op.drop_column("design_tokens", c)
    op.drop_index("uq_components_system_slug", table_name="components")
    op.drop_column("components", "slug")
    op.drop_index("uq_design_systems_slug", table_name="design_systems")
    op.drop_column("design_systems", "slug")
