"""Test harness. Uses an isolated PostgreSQL database (TEST_DATABASE_URL, default: the dev server's `dsrp_test`),
recreated from migrations once per session. All data below is explicitly labelled FIXTURE — never production records."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
_default = f"postgresql+psycopg://postgres@/dsrp_test?host={BACKEND / '.pgdata'}"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", _default)
os.environ["SECRET_KEY"] = "test-secret-key-" + "x" * 40
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOW_ANONYMOUS_READ"] = "false"
os.environ["STORAGE_DIR"] = str(BACKEND / "storage" / "test")
os.environ["DSKB_DATA_DIR"] = str(BACKEND / "storage" / "test" / "engine")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.core.security import create_session_token, hash_password  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402
from app.models import Source, User  # noqa: E402

FIXTURE_PW = "fixture-password-123"


@pytest.fixture(scope="session", autouse=True)
def _database():
    eng = create_engine(os.environ["DATABASE_URL"])
    with eng.begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"))
    eng.dispose()
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "app/database/migrations"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture(scope="session")
def users(_database):
    out = {}
    with SessionLocal() as s:
        for role in ("admin", "researcher", "viewer"):
            u = User(email=f"{role}@fixture.example", name=f"FIXTURE {role}", password_hash=hash_password(FIXTURE_PW), role=role)
            s.add(u)
            s.flush()
            out[role] = {"id": str(u.id), "email": u.email, "token": create_session_token(str(u.id), role)}
        s.commit()
    return out


@pytest.fixture(scope="session")
def client(_database):
    from app.main import app
    return TestClient(app)


def auth(users, role: str) -> dict:
    return {"Authorization": f"Bearer {users[role]['token']}"}


@pytest.fixture()
def as_admin(users):
    return auth(users, "admin")


@pytest.fixture()
def as_researcher(users):
    return auth(users, "researcher")


@pytest.fixture()
def as_viewer(users):
    return auth(users, "viewer")


@pytest.fixture(scope="session")
def fixture_source(_database):
    """A registered FIXTURE source (not one of the 20 seeds)."""
    with SessionLocal() as s:
        src = Source(key="FX1", name="FIXTURE source", url="https://fixture.example/docs", canonical_url="https://fixture.example/docs",
                     domain="fixture.example", source_type="documentation", adapter="generic", origin="user")
        s.add(src)
        s.commit()
        return src.id


def fixture_records(source_key: str, variant: int = 1) -> list[dict]:
    """Engine-shaped FIXTURE records: a library tool, a system listing, two components (one with props/keyboard),
    two tokens (one aliasing the other) and a guideline."""
    base = {"source_id": source_key, "secondary_categories": [], "tags": [], "relationships": [], "notes": ["FIXTURE"], "frameworks": ["React"],
            "technologies": [], "confidence": "high", "verification_status": "verified", "source_status": "official", "extraction_method": "document",
            "organization": "Fixture Org", "design_system": "Fixture UI", "source_version": f"0.{variant}.0"}
    recs = [
        {**base, "record_id": "sys:fx1:fixture-ui", "record_type": "system", "title": "Fixture Org — Fixture UI", "summary": "FIXTURE design system for tests.",
         "primary_category": "C12", "source_url": "https://fixture.example/docs",
         "normalized_content": {"name": "Fixture UI", "organization": "Fixture Org", "documentation_url": "https://fixture.example/docs", "source_attributes": {}}},
        {**base, "record_id": "cmp:fx1:dialog", "record_type": "component", "title": "Fixture UI: Dialog", "summary": "A FIXTURE modal dialog.",
         "primary_category": "C05", "source_url": "https://fixture.example/docs/dialog",
         "relationships": [{"type": "documented_by_system", "target": "sys:fx1:fixture-ui"}],
         "normalized_content": {"component_name": "Dialog", "library": "Fixture UI", "documentation_url": "https://fixture.example/docs/dialog", "detail_level": "api",
                                "props_count": 3, "subcomponents": [{"name": "Root", "props": [
                                    {"name": "open", "type": "boolean", "default": None, "description": "Controlled open state."},
                                    {"name": "defaultOpen", "type": "boolean", "default": "false", "description": "Initial state."},
                                    {"name": "onOpenChange", "type": "(open: boolean) => void", "default": None, "description": "Change handler."}]}],
                                "keyboard": [{"keys": "Escape", "description": "Closes the dialog.", "section": "Keyboard"}], "accessibility_notes": [{"section": "Accessibility", "text": "Traps focus."}]}},
        {**base, "record_id": "tok:fx1:brand", "record_type": "token", "title": "--fx-brand", "primary_category": "C03", "source_url": "https://fixture.example/docs/tokens",
         "normalized_content": {"token_name": "--fx-brand", "token_path": "--fx-brand", "token_type": "color", "raw_value": "#123456", "theme": "light", "source_format": "CSS custom property"}},
        {**base, "record_id": "tok:fx1:primary", "record_type": "token", "title": "--fx-primary", "primary_category": "C03", "source_url": "https://fixture.example/docs/tokens",
         "normalized_content": {"token_name": "--fx-primary", "token_path": "--fx-primary", "token_type": "color", "raw_value": "var(--fx-brand)", "alias_of": "--fx-brand", "theme": "light", "source_format": "CSS custom property"}},
        {**base, "record_id": "gdl:fx1:focus", "record_type": "guideline", "title": "Fixture checklist › Focus indicator", "summary": "Every interactive element shows a visible focus indicator.",
         "primary_category": "C07", "source_url": "https://fixture.example/docs/a11y", "normalized_content": {"kind": "checklist_item", "requirement": "Focus indicator"}},
    ]
    if variant == 1:
        recs.append({**base, "record_id": "cmp:fx1:legacy", "record_type": "component", "title": "Fixture UI: Legacy", "primary_category": "C05",
                     "source_url": "https://fixture.example/docs/legacy", "normalized_content": {"component_name": "Legacy", "library": "Fixture UI", "detail_level": "doc"}})
    return recs


def fixture_result(source_key: str, variant: int = 1) -> dict:
    return {"records": fixture_records(source_key, variant),
            "coverage": {"crawl_status": "inspected", "http_status": 200, "pages_attempted": 3, "pages_ok": 3, "errors": [], "limitations": ["FIXTURE run"]}}


@pytest.fixture(scope="session")
def built_kb(fixture_source):
    """Ingest FIXTURE records via the real ingest service and run a real build."""
    from app.models import Job
    from app.services import ingest, jobs as jobsvc
    from app.services.build import run_build
    with SessionLocal() as s:
        job = jobsvc.enqueue(s, "crawl", source_id=fixture_source, params={"fixture": True})
        src = s.get(Source, fixture_source)
        ingest.ingest(s, src, job.id, fixture_result(src.key, 1))
        jobsvc.finish(s, job.id, "succeeded")
        s.commit()
    with SessionLocal() as s:
        summary = run_build(s, None)
        s.commit()
    return summary


def new_uuid() -> str:
    return str(uuid.uuid4())
