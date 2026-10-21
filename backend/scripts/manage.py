"""Management commands.

    python scripts/manage.py seed                 # register the 20 seed sources (idempotent)
    python scripts/manage.py create-admin         # create/update the admin from ADMIN_EMAIL / ADMIN_PASSWORD
    python scripts/manage.py openapi out.json     # write the OpenAPI document
    python scripts/manage.py import-cache <dir>   # copy an existing engine HTTP cache (e.g. research/data/cache/http)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
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
    elif cmd == "create-admin":
        email, pw = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")
        if not email or not pw:
            from app.core.config import BACKEND_DIR
            from dotenv import dotenv_values
            env = dotenv_values(BACKEND_DIR / ".env")
            email, pw = email or env.get("ADMIN_EMAIL"), pw or env.get("ADMIN_PASSWORD")
        if not email or not pw or len(pw) < 12:
            sys.exit("ADMIN_EMAIL and ADMIN_PASSWORD (≥12 chars) are required")
        with session_scope() as db:
            u = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
            if u:
                u.password_hash, u.role, u.is_active = hash_password(pw), "admin", True
            else:
                db.add(User(email=email.lower(), name="Administrator", password_hash=hash_password(pw), role="admin"))
        print(f"admin ready: {email}")
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
