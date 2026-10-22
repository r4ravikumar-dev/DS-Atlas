"""One-command move of the knowledge base to Supabase (run from a trusted machine; secrets come from your shell, never from chat).

    export MIGRATION_DATABASE_URL='postgresql+psycopg://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require'
    export SUPABASE_URL='https://<ref>.supabase.co'
    export SUPABASE_SERVICE_ROLE_KEY='…'          # Project Settings → API keys (secret / service_role)
    cd backend && .venv/bin/python scripts/supabase_setup.py all --dump ../backups/<file>.dump

Steps (each idempotent; run one with `… <step>`):
  check    connect, report server version and whether the database is empty — prints hosts only, never credentials
  data     restore the dump into an EMPTY Supabase database (refuses if app tables already exist)
  schema   `alembic upgrade head` (creates the schema when you skip `data`) + Data API lockdown
  bucket   create the private Storage bucket (refuses a public bucket)
  objects  upload local raw snapshots/exports (STORAGE_DIR/objects) to the bucket; existing objects are skipped
  verify   row counts vs the local database, anon/authenticated privileges and RLS, bucket privacy
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
TABLES = ["design_systems", "system_resources", "components", "design_tokens", "guidelines", "records", "storybook_projects",
          "storybook_stories", "storybook_variants", "attribute_evidence", "sources", "users", "raw_documents", "system_aliases"]


def need(*names: str) -> None:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        sys.exit(f"Set {', '.join(missing)} in your shell first (see the header of this script).")


def normalize(url: str) -> str:
    """Accept the URI exactly as Supabase's Connect panel shows it (postgresql://…), adding the driver and TLS requirement."""
    url = url.strip()
    if "<" in url or ">" in url or "[YOUR-PASSWORD]" in url:
        sys.exit("MIGRATION_DATABASE_URL still contains a placeholder (<…> or [YOUR-PASSWORD]). Paste the Session pooler URI from "
                 "Supabase → Connect and put your database password in it.")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def mig_url() -> str:
    need("MIGRATION_DATABASE_URL")
    return normalize(os.environ["MIGRATION_DATABASE_URL"])


def safe(url: str) -> str:
    p = urlsplit(url)
    return f"{p.hostname}:{p.port or 5432}{p.path}"


def engine(url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool
    return create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None, "connect_timeout": 15})


def libpq(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def tool(name: str) -> str:
    local = BACKEND / ".venv/lib/python3.12/site-packages/pgserver/pginstall/bin" / name
    found = shutil.which(name) or (str(local) if local.exists() else None)
    if not found:
        sys.exit(f"{name} not found (install PostgreSQL client tools).")
    return found


def app_tables(url: str) -> int:
    from sqlalchemy import text
    with engine(url).connect() as c:
        return c.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename = ANY(:t)"), {"t": TABLES}).scalar()


def step_check() -> None:
    from sqlalchemy import text
    url = mig_url()
    if urlsplit(url).port == 6543:
        sys.exit("MIGRATION_DATABASE_URL must be the session pooler (5432) or direct connection, not the transaction pooler (6543).")
    with engine(url).connect() as c:
        ver = c.execute(text("SHOW server_version")).scalar()
        roles = c.execute(text("SELECT count(*) FROM pg_roles WHERE rolname IN ('anon','authenticated')")).scalar()
    print(f"connected to {safe(url)} — PostgreSQL {ver}; Supabase roles present: {roles == 2}; app tables present: {app_tables(url)}/{len(TABLES)}")


def step_data(dump: str | None) -> None:
    url = mig_url()
    if not dump or not Path(dump).exists():
        sys.exit("--dump <file> is required for `data` (e.g. ../backups/dsrp-…-for-supabase.dump).")
    n = app_tables(url)
    if n:
        print(f"skip data: the database already has {n} app tables (restore only into an empty project).")
        return
    cmd = [tool("pg_restore"), "--no-owner", "--no-privileges", "--no-comments", "--exit-on-error", "--single-transaction", "-d", libpq(url), dump]
    print(f"restoring {Path(dump).name} into {safe(url)} …")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # pg_restore errors name objects, not credentials; still, strip the connection string if it appears.
        sys.exit("pg_restore failed:\n" + r.stderr.replace(libpq(url), "<MIGRATION_DATABASE_URL>")[-3000:])
    print("restore complete")


def step_schema() -> None:
    url = mig_url()
    env = {**os.environ, "MIGRATION_DATABASE_URL": url, "DATABASE_URL": normalize(os.environ["DATABASE_URL"]) if os.environ.get("DATABASE_URL") else url}
    env.setdefault("SECRET_KEY", "x" * 48)  # settings validation only; alembic does not use it
    r = subprocess.run([str(BACKEND / ".venv/bin/alembic"), "upgrade", "head"], cwd=BACKEND, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("alembic upgrade failed:\n" + r.stderr.replace(url, "<MIGRATION_DATABASE_URL>")[-3000:])
    from sqlalchemy import text
    with engine(url).connect() as c:
        print(f"schema at {c.execute(text('SELECT version_num FROM alembic_version')).scalar()}; Data API lockdown applied")


def _supabase_storage():
    need("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
    from app.services.storage import SupabaseStorage
    return SupabaseStorage(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"], os.environ.get("SUPABASE_STORAGE_BUCKET", "dsrp-private"))


def step_bucket() -> None:
    st = _supabase_storage()
    print(f"bucket {st.bucket}: {st.ensure_bucket()} (private)")


def step_objects() -> None:
    st = _supabase_storage()
    root = Path(os.environ.get("STORAGE_DIR") or BACKEND / "storage") / "objects"
    files = sorted(p for p in root.rglob("*") if p.is_file())
    up = skip = 0
    for i, f in enumerate(files, 1):
        key = f.relative_to(root).as_posix()
        if st.exists(key):
            skip += 1
        else:
            st.put(key, f.read_bytes())
            up += 1
        if i % 200 == 0 or i == len(files):
            print(f"  {i}/{len(files)} (uploaded {up}, already present {skip})")
    print(f"objects: {up} uploaded, {skip} already present, from {root}")


def step_verify() -> None:
    from sqlalchemy import text
    from app.database.session import get_engine
    url = mig_url()
    with engine(url).connect() as remote, get_engine().connect() as local:
        rows = []
        for t in TABLES:
            r = remote.execute(text(f'SELECT count(*) FROM public."{t}"')).scalar()
            l = local.execute(text(f'SELECT count(*) FROM public."{t}"')).scalar()
            rows.append((t, l, r))
        priv = remote.execute(text("""SELECT count(*) FROM pg_tables t CROSS JOIN (VALUES ('anon'), ('authenticated')) r(role)
                                      WHERE t.schemaname='public' AND has_table_privilege(r.role, format('public.%I', t.tablename), 'SELECT')""")).scalar() \
            if remote.execute(text("SELECT count(*) FROM pg_roles WHERE rolname IN ('anon','authenticated')")).scalar() == 2 else 0
        no_rls = remote.execute(text("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                                        WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity""")).scalar()
    print(f"{'table':<22}{'local':>10}{'supabase':>10}")
    for t, l, r in rows:
        print(f"{t:<22}{l:>10}{r:>10}{'' if l == r else '  ≠'}")
    print(f"Data API: tables readable by anon/authenticated = {priv}; tables without RLS = {no_rls}")
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        st = _supabase_storage()
        print(f"bucket {st.bucket}: {st.ensure_bucket()} (private)")
    if priv or no_rls:
        sys.exit("Lockdown incomplete: run `scripts/supabase_setup.py schema` (or `manage.py supabase-lockdown`).")


def _friendly(e: Exception) -> str:
    msg = str(getattr(e, "orig", None) or e).splitlines()[0]
    for k in ("MIGRATION_DATABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        v = os.environ.get(k)
        if v:
            msg = msg.replace(v, f"<{k}>")
    return msg


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["check", "data", "schema", "bucket", "objects", "verify", "all"])
    ap.add_argument("--dump", help="pg_dump -Fc file to restore (step `data`)")
    a = ap.parse_args()
    steps = ["check", "data", "schema", "bucket", "objects", "verify"] if a.step == "all" else [a.step]
    from sqlalchemy.exc import OperationalError
    for s in steps:
        print(f"── {s}")
        try:
            {"check": step_check, "data": lambda: step_data(a.dump), "schema": step_schema, "bucket": step_bucket,
             "objects": step_objects, "verify": step_verify}[s]()
        except OperationalError as e:
            sys.exit(f"Could not connect to the database: {_friendly(e)}\n"
                     "Check the Session pooler host/port (5432) and password from Supabase → Connect.")


if __name__ == "__main__":
    main()
