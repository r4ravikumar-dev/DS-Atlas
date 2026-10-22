"""Management commands.

    python scripts/manage.py seed                 # register the 20 seed sources (idempotent)
    python scripts/manage.py bootstrap-admin      # one-shot: first admin from ADMIN_EMAIL / ADMIN_PASSWORD; refuses once any admin exists
    python scripts/manage.py reset-admin-password <email>  # shell-only recovery; password via ADMIN_PASSWORD or hidden prompt
    python scripts/manage.py setup-storage        # Supabase: create the private storage bucket (idempotent)
    python scripts/manage.py supabase-lockdown    # Supabase: revoke Data API access + enable RLS on all tables (idempotent)
    python scripts/manage.py openapi out.json     # write the OpenAPI document
    python scripts/manage.py import-cache <dir>   # copy an existing engine HTTP cache (e.g. research/data/cache/http)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database.session import session_scope  # noqa: E402
from app.models import User  # noqa: E402
from app.services.sources import seed_sources  # noqa: E402


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "seed":
        with session_scope() as db:
            print(f"registered {seed_sources(db)} new source(s)")
    elif cmd in ("bootstrap-admin", "create-admin"):
        # One-shot: only works while no administrator exists. Requires shell access to the server; no HTTP equivalent exists.
        email, pw = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")
        if not email or not pw:
            from app.core.config import BACKEND_DIR
            from dotenv import dotenv_values
            env = dotenv_values(BACKEND_DIR / ".env")
            email, pw = email or env.get("ADMIN_EMAIL"), pw or env.get("ADMIN_PASSWORD")
        if not email or not pw or len(pw) < 12:
            sys.exit("ADMIN_EMAIL and ADMIN_PASSWORD (>=12 chars) are required")
        from app.services.audit import audit
        with session_scope() as db:
            if db.scalar(select(User.id).where(User.role == "admin").limit(1)):
                sys.exit("An administrator already exists; bootstrap is disabled. "
                         "Use `manage.py reset-admin-password <email>` to recover the account.")
            if db.scalar(select(User.id).where(func.lower(User.email) == email.lower())):
                sys.exit("A deactivated account with this email exists; resolve it before bootstrapping.")
            u = User(email=email.lower(), name="Administrator", password_hash=hash_password(pw), role="admin",
                     email_verified_at=datetime.now(timezone.utc))
            db.add(u)
            db.flush()
            audit(db, None, "admin.bootstrap", "user", u.id)
        print(f"bootstrap admin created: {email}")
    elif cmd == "reset-admin-password":
        # Recovery from the server shell only. The new password is read from ADMIN_PASSWORD or typed (not echoed); never a CLI argument.
        import getpass
        from app.services.audit import audit
        target = (sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ADMIN_EMAIL") or "").lower()
        pw = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("New administrator password (>=12 chars): ")
        if not target or len(pw) < 12:
            sys.exit("usage: manage.py reset-admin-password <admin-email>  (password >=12 chars via ADMIN_PASSWORD or prompt)")
        with session_scope() as db:
            u = db.scalar(select(User).where(func.lower(User.email) == target, User.role == "admin"))
            if not u:
                sys.exit("No administrator with that email.")
            u.password_hash, u.is_active = hash_password(pw), True
            u.session_version += 1  # sign out every existing session
            audit(db, None, "admin.password_reset_cli", "user", u.id)
        print(f"password reset for {target}; all sessions signed out")
    elif cmd == "setup-storage":
        # Supabase Storage: create the private bucket used for raw snapshots and exports (idempotent).
        from app.services.storage import SupabaseStorage, storage
        st = storage()
        if not isinstance(st, SupabaseStorage):
            sys.exit("STORAGE_BACKEND is not 'supabase'; local storage needs no setup.")
        print(f"bucket {st.bucket}: {st.ensure_bucket()} (private)")
    elif cmd == "supabase-lockdown":
        # Re-apply the Data API lockdown without a migration (it also runs after every `alembic upgrade`).
        from app.database.session import get_engine
        from app.database.supabase import lockdown
        with get_engine().begin() as conn:
            print(f"locked down {lockdown(conn)['tables']} table(s)")
    elif cmd == "openapi":
        from app.main import app
        Path(sys.argv[2]).write_text(json.dumps(app.openapi(), indent=2))
        print(f"wrote {sys.argv[2]}")
    elif cmd == "import-cache":
        from app.scrapers.dskb.core import CACHE
        src, dst = Path(sys.argv[2]), CACHE / "http"
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in src.iterdir():
            if not (dst / f.name).exists():
                shutil.copy2(f, dst / f.name)
                n += 1
        print(f"imported {n} cache file(s) into {dst}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
