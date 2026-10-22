"""Supabase deployment pieces: Storage adapter (mocked HTTP), Data API lockdown (real PostgreSQL roles), pooler detection."""
from __future__ import annotations

import json

import httpx
import pytest
from sqlalchemy import text

from app.database.session import SessionLocal, get_engine, uses_transaction_pooler
from app.database.supabase import lockdown
from app.services.storage import SupabaseStorage, StorageError

KEY = "service-role-FIXTURE-not-a-real-key"


def _store(handler) -> tuple[SupabaseStorage, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def h(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return handler(req)
    return SupabaseStorage("https://proj.supabase.co", KEY, "dsrp-private", ttl=60, client=httpx.Client(transport=httpx.MockTransport(h))), seen


def test_upload_is_private_inert_and_idempotent():
    st, seen = _store(lambda r: httpx.Response(201, json={"Key": "x"}))
    assert st.put("raw/ab/abc", b"<html>") == "raw/ab/abc"
    req = seen[0]
    assert str(req.url) == "https://proj.supabase.co/storage/v1/object/dsrp-private/raw/ab/abc"
    assert req.headers["x-upsert"] == "false" and req.headers["content-type"] == "application/octet-stream"
    assert req.headers["authorization"] == f"Bearer {KEY}" and req.headers["apikey"] == KEY
    dup, _ = _store(lambda r: httpx.Response(400, json={"statusCode": "409", "error": "Duplicate", "message": "The resource already exists"}))
    assert dup.put("raw/ab/abc", b"<html>") == "raw/ab/abc"


def test_errors_do_not_echo_response_bodies():
    st, _ = _store(lambda r: httpx.Response(500, text="internal detail " + KEY))
    with pytest.raises(StorageError) as e:
        st.put("exports/j/x.csv", b"a")
    assert KEY not in str(e.value) and "500" in str(e.value)


def test_exists_and_read():
    st, _ = _store(lambda r: httpx.Response(200 if r.url.path.endswith("/there") else 400, content=b"data"))
    assert st.exists("raw/there") and not st.exists("raw/missing")
    assert st.read("raw/there") == b"data"


@pytest.mark.parametrize("bad", ["/etc/passwd", "raw/../secret", ""])
def test_rejects_unsafe_keys(bad):
    st, _ = _store(lambda r: httpx.Response(200))
    with pytest.raises(ValueError):
        st.exists(bad)


def test_download_is_a_short_lived_signed_attachment_link():
    def h(r: httpx.Request) -> httpx.Response:
        assert r.url.path == "/storage/v1/object/sign/dsrp-private/exports/j1/report.csv"
        assert json.loads(r.content) == {"expiresIn": 60, "download": "report.csv"}
        return httpx.Response(200, json={"signedURL": "/object/sign/dsrp-private/exports/j1/report.csv?token=abc"})
    st, _ = _store(h)
    resp = st.download_response("exports/j1/report.csv", "report.csv")
    assert resp.status_code == 303
    loc = resp.headers["location"]
    assert loc.startswith("https://proj.supabase.co/storage/v1/object/sign/dsrp-private/exports/j1/report.csv?token=abc")
    assert "download=report.csv" in loc and KEY not in loc
    assert resp.headers["cache-control"] == "no-store"


def test_public_bucket_is_refused():
    st, _ = _store(lambda r: httpx.Response(200, json={"id": "dsrp-private", "public": True}))
    with pytest.raises(StorageError):
        st.ensure_bucket()


@pytest.mark.parametrize("url,mode,expected", [
    ("postgresql+psycopg://postgres.ref:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres", "auto", True),
    ("postgresql+psycopg://postgres.ref:pw@aws-0-eu-central-1.pooler.supabase.com:5432/postgres", "auto", False),
    ("postgresql+psycopg://postgres@/dsrp?host=/tmp", "auto", False),
    ("postgresql+psycopg://u:p@db:5432/x", "transaction", True),
])
def test_transaction_pooler_detection(url, mode, expected):
    assert uses_transaction_pooler(url, mode) is expected


def test_lockdown_closes_the_data_api_roles(_database):
    eng = get_engine()
    with eng.begin() as c:
        assert lockdown(c) == {"tables": 0}  # plain PostgreSQL: no-op
        for r in ("anon", "authenticated"):
            c.execute(text(f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{r}') THEN CREATE ROLE {r} NOLOGIN; END IF; END $$"))
        c.execute(text("GRANT USAGE ON SCHEMA public TO anon, authenticated"))
        c.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated"))
        assert c.execute(text("SELECT has_table_privilege('anon', 'public.users', 'SELECT')")).scalar() is True
    try:
        with eng.begin() as c:
            out = lockdown(c)
        with eng.connect() as c:
            assert out["tables"] > 20
            for r in ("anon", "authenticated"):
                for t in ("users", "design_systems", "system_resources", "raw_documents"):
                    assert c.execute(text(f"SELECT has_table_privilege('{r}', 'public.{t}', 'SELECT')")).scalar() is False
            assert c.execute(text("SELECT bool_and(relrowsecurity) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                                  "WHERE n.nspname = 'public' AND c.relkind = 'r'")).scalar() is True
        with SessionLocal() as s:  # the owner role used by the app is unaffected by RLS
            assert s.execute(text("SELECT count(*) FROM users")).scalar() >= 0
    finally:
        with eng.begin() as c:
            for t in c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars():
                c.execute(text(f'ALTER TABLE public."{t}" DISABLE ROW LEVEL SECURITY'))
            c.execute(text("REVOKE ALL ON SCHEMA public FROM anon, authenticated"))
            c.execute(text("DROP OWNED BY anon, authenticated"))
            c.execute(text("DROP ROLE anon"))
            c.execute(text("DROP ROLE authenticated"))
