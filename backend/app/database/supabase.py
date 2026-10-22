"""Supabase hardening, applied after every `alembic upgrade` (idempotent).

Supabase exposes the `public` schema through its auto-generated Data API (PostgREST) to the `anon` and `authenticated`
roles. This application never uses that API: every read and write goes through the FastAPI backend, which enforces the
administrator session. So on any database where those roles exist, the app's tables are closed to them:

* all privileges on tables, sequences and functions in `public` are revoked from `anon` and `authenticated`, including
  default privileges for tables created later by the migrating role;
* row-level security is enabled on every table with no policies, so even an accidental re-grant returns nothing.

The application connects as the table owner (`postgres`), which is not subject to RLS on its own tables.
On plain PostgreSQL (development, tests) the roles do not exist and this is a no-op.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

API_ROLES = ("anon", "authenticated")


def is_supabase(conn: Connection) -> bool:
    return bool(conn.execute(text("SELECT count(*) FROM pg_roles WHERE rolname = ANY(:r)"), {"r": list(API_ROLES)}).scalar() == len(API_ROLES))


def lockdown(conn: Connection) -> dict[str, int]:
    if not is_supabase(conn):
        return {"tables": 0}
    roles = ", ".join(API_ROLES)
    for kind in ("TABLES", "SEQUENCES", "FUNCTIONS"):
        conn.execute(text(f"REVOKE ALL ON ALL {kind} IN SCHEMA public FROM {roles}"))
        conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON {kind} FROM {roles}"))
    tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars().all()
    for t in tables:
        conn.execute(text(f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY'))
    return {"tables": len(tables)}
