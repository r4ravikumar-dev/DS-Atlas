"""SQLAlchemy engine/session factory with pooling and statement timeouts."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from ..core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: sessionmaker | None = None


def uses_transaction_pooler(url: str, mode: str = "auto") -> bool:
    """Transaction-mode poolers (Supabase Supavisor :6543, PgBouncer) share server connections between clients per transaction."""
    if mode != "auto":
        return mode == "transaction"
    return make_url(url).port == 6543


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        s = get_settings()
        if uses_transaction_pooler(s.database_url, s.db_pool_mode):
            # The pooler does the pooling (and serverless instances come and go): no client-side pool, and no prepared
            # statements or session-level SETs, which would leak across the clients sharing a server connection.
            _engine = create_engine(s.database_url, poolclass=NullPool, connect_args={"prepare_threshold": None}, future=True)
        else:
            _engine = create_engine(s.database_url, pool_size=s.db_pool_size, max_overflow=s.db_pool_size, pool_pre_ping=True, future=True)

            @event.listens_for(_engine, "connect")
            def _on_connect(dbapi_conn, _):  # noqa: ANN001
                with dbapi_conn.cursor() as cur:
                    cur.execute(f"SET statement_timeout = {int(s.db_statement_timeout_ms)}")
                dbapi_conn.commit()

        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def SessionLocal() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
