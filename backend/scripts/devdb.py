"""Local development PostgreSQL (embedded binaries via `pgserver`). Not used in production.

    python scripts/devdb.py start   # starts (or reuses) a persistent server, creates database `dsrp`, prints DATABASE_URL
    python scripts/devdb.py stop
    python scripts/devdb.py url
"""
from __future__ import annotations

import sys
from pathlib import Path

import pgserver

DATA = Path(__file__).resolve().parents[1] / ".pgdata"


def server():
    return pgserver.get_server(str(DATA), cleanup_mode=None)


def url(db: str = "dsrp") -> str:
    return f"postgresql+psycopg://postgres@/{db}?host={DATA}"


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd == "start":
        srv = server()
        for db in ("dsrp", "dsrp_test"):
            if db not in srv.psql(f"SELECT datname FROM pg_database WHERE datname='{db}';"):
                srv.psql(f"CREATE DATABASE {db};")
        print(url())
    elif cmd == "stop":
        import subprocess
        subprocess.run([str(Path(pgserver.__file__).parent / "pginstall" / "bin" / "pg_ctl"), "-D", str(DATA), "stop", "-m", "fast"], check=False)
    elif cmd == "url":
        print(url())


if __name__ == "__main__":
    main()
