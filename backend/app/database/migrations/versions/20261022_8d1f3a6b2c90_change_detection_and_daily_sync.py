"""content fingerprints / content timestamps, source change tracking, record_changes, sync_schedule, sync_runs

Revision ID: 8d1f3a6b2c90
Revises: 5b2e9a1c7d40
Create Date: 2026-10-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8d1f3a6b2c90"
down_revision = "5b2e9a1c7d40"
branch_labels = None
depends_on = None

ENTITY_TABLES = ("records", "design_systems", "components", "design_tokens", "guidelines")


def upgrade() -> None:
    for t in ENTITY_TABLES:
        op.add_column(t, sa.Column("fingerprint", sa.String(64)))
        op.add_column(t, sa.Column("content_updated_at", sa.DateTime(timezone=True)))
    # Baseline: existing content counts as last changed when it was last written (fingerprints are filled by the next run
    # without bumping these timestamps).
    op.execute("UPDATE records SET content_updated_at = updated_at")
    op.execute("UPDATE design_systems SET content_updated_at = updated_at")
    for t in ("components", "design_tokens", "guidelines"):
        op.execute(f"UPDATE {t} x SET content_updated_at = r.updated_at FROM records r WHERE r.id = x.record_id")
    op.add_column("sources", sa.Column("last_content_hash", sa.String(64)))
    op.add_column("sources", sa.Column("last_content_changed_at", sa.DateTime(timezone=True)))
    op.add_column("sources", sa.Column("last_change_summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("sources", sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "record_changes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("sync_run_id", postgresql.UUID(as_uuid=True)),
        sa.Column("job_id", postgresql.UUID(as_uuid=True)),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="SET NULL")),
        sa.Column("record_key", sa.String(400), nullable=False),
        sa.Column("record_type", sa.String(30), nullable=False),
        sa.Column("change", sa.String(20), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for c in ("sync_run_id", "job_id", "source_id", "record_key", "change", "at"):
        op.create_index(f"ix_record_changes_{c}", "record_changes", [c])

    op.create_table(
        "sync_schedule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("hour_utc", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("minute_utc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_id", postgresql.UUID(as_uuid=True)),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_sync_schedule_singleton"),
    )
    op.execute("""INSERT INTO sync_schedule (id, enabled, interval_hours, hour_utc, minute_utc, next_run_at)
                  VALUES (1, true, 24, 3, 0, (date_trunc('day', now() AT TIME ZONE 'UTC') + interval '1 day 3 hours') AT TIME ZONE 'UTC')""")

    op.create_table(
        "sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trigger", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="running"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("built", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sources", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sync_runs_status", "sync_runs", ["status"])
    op.create_index("ix_sync_runs_started_at", "sync_runs", ["started_at"])
    # at most one run in progress at a time
    op.create_index("uq_sync_runs_one_running", "sync_runs", ["status"], unique=True, postgresql_where=sa.text("status = 'running'"))


def downgrade() -> None:
    op.drop_table("sync_runs")
    op.drop_table("sync_schedule")
    op.drop_table("record_changes")
    for c in ("consecutive_failures", "last_change_summary", "last_content_changed_at", "last_content_hash"):
        op.drop_column("sources", c)
    for t in ENTITY_TABLES:
        op.drop_column(t, "content_updated_at")
        op.drop_column(t, "fingerprint")
