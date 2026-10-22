"""Management commands.

    python scripts/manage.py seed                 # register the 20 seed sources (idempotent)
    python scripts/manage.py bootstrap-admin      # one-shot: first admin from ADMIN_EMAIL / ADMIN_PASSWORD; refuses once any admin exists
    python scripts/manage.py issue-reset <email>  # email a single-use password-reset link to an existing user
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
                sys.exit("An administrator already exists; bootstrap is disabled. Invite users from the admin UI, "
                         "or use `manage.py issue-reset <email>` to recover an admin account.")
            if db.scalar(select(User.id).where(func.lower(User.email) == email.lower())):
                sys.exit("A non-admin user with this email exists; promote them from an admin session instead.")
            u = User(email=email.lower(), name="Administrator", password_hash=hash_password(pw), role="admin",
                     email_verified_at=datetime.now(timezone.utc))
            db.add(u)
            db.flush()
            audit(db, None, "admin.bootstrap", "user", u.id)
        print(f"bootstrap admin created: {email}")
    elif cmd == "issue-reset":
        # Recovery path: emails a single-use, 2-hour reset link (+ verification code) to an existing active user.
        from app.services import invitations
        target = sys.argv[2].lower() if len(sys.argv) > 2 else sys.exit("usage: manage.py issue-reset <email>")
        with session_scope() as db:
            u = db.scalar(select(User).where(func.lower(User.email) == target, User.is_active.is_(True)))
            if not u:
                sys.exit("No active user with that email.")
            inv = invitations.create(db, email=u.email, role=u.role, invited_by=None, ttl_hours=2, kind="reset")
            print(f"reset invitation {inv.id}: delivery={inv.delivery_status}")
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
