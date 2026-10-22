"""Daily synchronization against controllable FIXTURE sources (no network): cases A–G from the spec plus scheduler coordination.
Jobs run through the real worker handlers (`app.workers.main.execute`), so crawl → ingest → finalize → build is exercised end to end."""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text, update

from app.core.exceptions import Conflict
from app.database.session import SessionLocal
from app.models import Component, DesignSystem, DesignToken, Job, Record, RecordChange, Source, SyncRun, SyncSchedule
from app.services import jobs as jobsvc
from app.services import sync as syncsvc

FIX: dict[str, dict] = {}  # source key -> {"records": [...], "status": ..., "errors": [...], "raise": Exception | None}
BASE = {"secondary_categories": [], "tags": [], "relationships": [], "notes": ["FIXTURE"], "frameworks": ["React"], "technologies": [],
        "confidence": "medium", "verification_status": "unverified", "source_status": "third_party", "extraction_method": "html", "source_version": None}


def sysrec(src, slug, name, docs, org="FIXTURE Org"):
    return {**BASE, "source_id": src, "record_id": f"sys:{src.lower()}:{slug}", "record_type": "system", "title": name, "summary": f"FIXTURE {name}",
            "primary_category": "C12", "source_url": f"https://{src.lower()}.fixture.example/{slug}", "organization": org, "design_system": name,
            "normalized_content": {"name": name, "organization": org, "documentation_url": docs, "source_attributes": {}}}


def comprec(src, slug, name, system_slug):
    return {**BASE, "source_id": src, "record_id": f"cmp:{src.lower()}:{slug}", "record_type": "component", "title": name, "primary_category": "C05",
            "source_url": f"https://{src.lower()}.fixture.example/c/{slug}", "organization": None, "design_system": None,
            "relationships": [{"type": "documented_by_system", "target": f"sys:{src.lower()}:{system_slug}"}],
            "normalized_content": {"component_name": name, "library": None, "detail_level": "doc"}}


def tokrec(src, slug, path, value, system_slug):
    return {**BASE, "source_id": src, "record_id": f"tok:{src.lower()}:{slug}", "record_type": "token", "title": path, "primary_category": "C03",
            "source_url": f"https://{src.lower()}.fixture.example/tokens", "organization": None, "design_system": None,
            "relationships": [{"type": "token_of", "target": f"sys:{src.lower()}:{system_slug}"}],
            "normalized_content": {"token_name": path, "token_path": path, "token_type": "color", "raw_value": value, "source_format": "CSS custom property"}}


def fixture_adapter(seed):
    f = FIX[seed["source_id"]]
    if f.get("raise"):
        raise f["raise"]
    return {"records": [dict(r, relationships=list(r["relationships"]), notes=list(r["notes"])) for r in f["records"]],
            "coverage": {"crawl_status": f.get("status", "inspected"), "errors": list(f.get("errors", [])), "pages_attempted": 1, "pages_ok": 1}}


@pytest.fixture(scope="module")
def srcs(_database):
    with SessionLocal() as s:
        ids = {}
        for key in ("SYNC1", "SYNC2"):
            src = Source(key=key, name=f"FIXTURE {key}", url=f"https://{key.lower()}.fixture.example/", canonical_url=f"https://{key.lower()}.fixture.example/",
                         domain=f"{key.lower()}.fixture.example", source_type="directory", adapter="fixture_sync", origin="user")
            s.add(src)
            s.flush()
            ids[key] = src.id
        s.commit()
    FIX["SYNC1"] = {"records": [sysrec("SYNC1", "nova", "Nova DS", "https://nova.fixture.example/"),
                                comprec("SYNC1", "nova-button", "Button", "nova"),
                                tokrec("SYNC1", "nova-blue", "--nova-blue", "#0000ff", "nova"),
                                tokrec("SYNC1", "nova-red", "--nova-red", "#ff0000", "nova")]}
    FIX["SYNC2"] = {"records": [sysrec("SYNC2", "lumen", "Lumen DS", "https://lumen.fixture.example/")]}
    return ids


@pytest.fixture(autouse=True)
def _adapter(monkeypatch):
    from app.workers import crawl
    monkeypatch.setitem(crawl.ADAPTERS, "fixture_sync", fixture_adapter)
    monkeypatch.setattr(syncsvc, "RETRY_DELAY", timedelta(0))


def drain(limit: int = 200) -> None:
    """Run queued jobs in-process until none are left (waiting jobs are made due immediately)."""
    from app.workers.main import execute
    for _ in range(limit):
        with SessionLocal() as db:
            db.execute(update(Job).where(Job.status == "queued").values(run_after=datetime.now(timezone.utc) - timedelta(seconds=1)))
            db.commit()
            job = jobsvc.claim(db, "pytest", None)
        if not job:
            return
        execute(job.id)
    raise AssertionError("jobs did not drain")


def run_sync(srcs, keys=("SYNC1", "SYNC2")) -> SyncRun:
    with SessionLocal() as db:
        run = syncsvc.start_run(db, "manual", source_ids=[srcs[k] for k in keys])
        db.commit()
        rid = run.id
    drain()
    with SessionLocal() as db:
        return db.get(SyncRun, rid)


def system(name):
    with SessionLocal() as db:
        return db.scalar(select(DesignSystem).where(DesignSystem.name == name))


def snapshot():
    with SessionLocal() as db:
        return {"systems": {d.key: (d.id, d.fingerprint, d.content_updated_at) for d in db.scalars(select(DesignSystem))},
                "components": {c.record_id: (c.id, c.fingerprint, c.content_updated_at) for c in db.scalars(select(Component))},
                "tokens": {t.record_id: (t.id, t.fingerprint, t.content_updated_at, t.raw_value) for t in db.scalars(select(DesignToken))},
                "records": {r.record_key: (r.id, r.fingerprint, r.content_updated_at) for r in db.scalars(select(Record))},
                "changes": db.scalar(select(func.count()).select_from(RecordChange))}


def test_first_run_creates_then_identical_run_changes_nothing(srcs):
    first = run_sync(srcs)
    assert first.status == "succeeded" and first.built and first.metrics["new_systems"] >= 2
    nova = system("Nova DS")
    assert nova and nova.component_count == 1 and nova.token_count == 2
    before = snapshot()
    with SessionLocal() as db:
        checked_before = db.get(Source, srcs["SYNC1"]).last_attempted_at
    # Case A — no changes
    second = run_sync(srcs)
    after = snapshot()
    assert second.status == "succeeded" and not second.built
    m = second.metrics
    assert (m["sources_unchanged"], m["sources_changed"], m["records_created"], m["records_updated"]) == (2, 0, 0, 0)
    assert after == before  # same ids, fingerprints and content timestamps; no change-history rows
    with SessionLocal() as db:
        assert db.get(Source, srcs["SYNC1"]).last_attempted_at > checked_before  # operational "last checked" still moves


def test_new_system_is_added_once_and_published(srcs, client):
    FIX["SYNC2"]["records"].append(sysrec("SYNC2", "orion", "Orion DS", "https://orion.fixture.example/"))  # Case B
    run = run_sync(srcs)
    assert run.metrics["new_systems"] == 1 and run.metrics["sources_changed"] == 1
    client.cookies.clear()
    hits = client.get("/api/v1/design-systems", params={"q": "Orion"}).json()["data"]  # public, no account
    assert [h["name"] for h in hits] == ["Orion DS"]
    again = run_sync(srcs)
    assert again.metrics["new_systems"] == 0 and not again.built
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(DesignSystem).where(DesignSystem.name == "Orion DS")) == 1


def test_new_component_attaches_without_touching_existing_ones(srcs, client):
    before = snapshot()
    FIX["SYNC1"]["records"].append(comprec("SYNC1", "nova-dialog", "Dialog", "nova"))  # Case C
    run = run_sync(srcs)
    assert run.metrics["new_components"] == 1 and run.metrics["components_updated"] == 0
    after = snapshot()
    for rid, v in before["components"].items():
        assert after["components"][rid] == v  # existing components: same id, fingerprint, content timestamp
    nova = system("Nova DS")
    assert nova.component_count == 2
    names = {c["name"] for c in client.get("/api/v1/components", params={"q": "Dialog"}).json()["data"]}
    assert "Dialog" in names


def test_changed_token_updates_only_that_token(srcs):
    before = snapshot()
    rec = next(r for r in FIX["SYNC1"]["records"] if r["record_id"] == "tok:sync1:nova-blue")  # Case D
    rec["normalized_content"] = {**rec["normalized_content"], "raw_value": "#0011ff"}
    run = run_sync(srcs)
    assert run.metrics["records_updated"] == 1 and run.metrics["tokens_updated"] == 1 and run.metrics["new_tokens"] == 0
    after = snapshot()
    changed = [k for k in before["tokens"] if after["tokens"][k] != before["tokens"][k]]
    assert len(changed) == 1 and after["tokens"][changed[0]][3] == "#0011ff" and after["tokens"][changed[0]][0] == before["tokens"][changed[0]][0]
    assert all(after["components"][k] == v for k, v in before["components"].items())
    with SessionLocal() as db:
        ch = db.scalars(select(RecordChange).where(RecordChange.sync_run_id == run.id)).all()
        assert [(c.record_key, c.change) for c in ch] == [("tok:sync1:nova-blue", "updated")]


def test_source_outage_preserves_data_and_retries(srcs, client):
    FIX["SYNC1"]["raise"] = TimeoutError("read timed out")  # Case E
    try:
        run = run_sync(srcs)
    finally:
        FIX["SYNC1"].pop("raise")
    s1 = next(s for s in run.sources if s["key"] == "SYNC1")
    assert s1["outcome"] == "failed" and s1["attempts"] == 2 and s1["records_preserved"] >= 4  # retried once, then gave up for today
    assert run.status == "partially_succeeded" and run.metrics["sources_failed"] == 1 and not run.built
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Record).where(Record.source_id == srcs["SYNC1"], Record.is_stale.is_(False))) >= 5
        assert db.get(Source, srcs["SYNC1"]).consecutive_failures >= 1
    assert client.get("/api/v1/design-systems", params={"q": "Nova"}).json()["data"]  # still public


def test_rate_limited_partial_crawl_never_hides_records(srcs):
    keep = FIX["SYNC1"]["records"]
    FIX["SYNC1"].update(records=keep[:1], status="inspected_partial", errors=["HTTP 429 Too Many Requests (Retry-After: 120)"])  # Case F
    try:
        run = run_sync(srcs)
    finally:
        FIX["SYNC1"].update(records=keep, status="inspected", errors=[])
    s1 = next(s for s in run.sources if s["key"] == "SYNC1")
    s2 = next(s for s in run.sources if s["key"] == "SYNC2")
    assert s1["stale_suppressed"] >= 4 and s1["records_marked_stale"] == 0 and s1["partial"]
    assert s2["outcome"] == "unchanged" and run.status == "partially_succeeded"
    assert system("Nova DS").component_count == 2  # nothing hidden


def test_second_directory_listing_attaches_to_existing_system(srcs):
    FIX["SYNC2"]["records"].append(sysrec("SYNC2", "nova-again", "Nova DS", "https://nova.fixture.example/"))  # Case G
    run = run_sync(srcs)
    assert run.metrics["new_systems"] == 0
    with SessionLocal() as db:
        novas = db.scalars(select(DesignSystem).where(DesignSystem.name == "Nova DS")).all()
        assert len(novas) == 1 and set(novas[0].source_keys) == {"SYNC1", "SYNC2"}


# ───────────────────────────── scheduler ─────────────────────────────

def test_next_slot_is_the_next_utc_time_of_day():
    t = datetime(2026, 10, 22, 2, 59, tzinfo=timezone.utc)
    assert syncsvc.next_slot(t, 3, 0) == datetime(2026, 10, 22, 3, 0, tzinfo=timezone.utc)
    assert syncsvc.next_slot(datetime(2026, 10, 22, 3, 0, tzinfo=timezone.utc), 3, 0) == datetime(2026, 10, 23, 3, 0, tzinfo=timezone.utc)
    assert syncsvc.next_slot(datetime(2026, 10, 22, 23, 30, tzinfo=timezone.utc), 3, 0) == datetime(2026, 10, 23, 3, 0, tzinfo=timezone.utc)


@pytest.fixture()
def only_fixture_sources(srcs):
    """The scheduler crawls every enabled source; keep it to the FIXTURE sync sources for these tests."""
    with SessionLocal() as db:
        paused = db.scalars(select(Source.id).where(Source.is_paused.is_(False), Source.id.not_in(list(srcs.values())))).all()
        db.execute(update(Source).where(Source.id.in_(paused)).values(is_paused=True))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(update(Source).where(Source.id.in_(paused)).values(is_paused=False))
        db.commit()


def test_due_run_is_claimed_exactly_once_across_concurrent_schedulers(only_fixture_sources):
    due = datetime.now(timezone.utc) - timedelta(minutes=1)
    with SessionLocal() as db:
        db.execute(update(SyncSchedule).where(SyncSchedule.id == 1).values(enabled=True, next_run_at=due))
        db.commit()
    started, barrier = [], threading.Barrier(4)

    def worker():
        barrier.wait()
        with SessionLocal() as db:
            run = syncsvc.tick(db)
            db.commit()
            if run:
                started.append(run.id)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(started) == 1
    with SessionLocal() as db:
        sch = db.get(SyncSchedule, 1)
        assert sch.next_run_at > datetime.now(timezone.utc) and sch.last_run_id == started[0]
        assert db.scalar(select(func.count()).select_from(SyncRun).where(SyncRun.status == "running")) == 1
        with pytest.raises(Conflict):  # manual and scheduled runs never overlap
            syncsvc.start_run(db, "manual")
        db.rollback()
        assert syncsvc.tick(db) is None  # not due again until tomorrow
        db.rollback()
    drain()
    with SessionLocal() as db:
        run = db.get(SyncRun, started[0])
        assert run.trigger == "scheduled" and run.status == "succeeded" and run.scheduled_for == due


def test_schedule_persists_and_disabling_stops_runs(only_fixture_sources, client, as_admin):
    r = client.patch("/api/v1/admin/sync/schedule", headers=as_admin, json={"enabled": False, "hour_utc": 4, "minute_utc": 15})
    assert r.status_code == 200 and r.json()["data"]["enabled"] is False and r.json()["data"]["hour_utc"] == 4
    with SessionLocal() as db:  # a fresh session (= after a restart) sees the same persisted schedule
        sch = db.get(SyncSchedule, 1)
        assert (sch.enabled, sch.hour_utc, sch.minute_utc) == (False, 4, 15)
        assert sch.next_run_at.astimezone(timezone.utc).hour == 4
        db.execute(update(SyncSchedule).values(next_run_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
        db.commit()
        assert syncsvc.tick(db) is None  # disabled: nothing starts
        db.commit()
    client.patch("/api/v1/admin/sync/schedule", headers=as_admin, json={"enabled": True, "hour_utc": 3, "minute_utc": 0})


def test_admin_sync_endpoints_report_runs(srcs, client, as_admin):
    st = client.get("/api/v1/admin/sync", headers=as_admin).json()["data"]
    assert st["timezone"] == "UTC" and st["next_run_at"] and st["last_run"]
    runs = client.get("/api/v1/admin/sync/runs", headers=as_admin).json()
    assert runs["meta"]["total_items"] >= 8
    detail = client.get(f"/api/v1/admin/sync/runs/{runs['data'][0]['id']}", headers=as_admin).json()["data"]
    assert detail["sources"] and "sources_checked" in detail["metrics"]
    ch = client.get("/api/v1/admin/changes", headers=as_admin, params={"change": "updated"}).json()
    assert any(c["record_key"] == "tok:sync1:nova-blue" for c in ch["data"])
    client.cookies.clear()
    assert client.get("/api/v1/admin/sync").status_code == 401 and client.post("/api/v1/admin/sync/run").status_code == 401


def test_abandoned_run_is_marked_interrupted():
    with SessionLocal() as db:
        db.execute(text("UPDATE sync_runs SET status = 'succeeded' WHERE status = 'running'"))
        run = SyncRun(trigger="manual", status="running", started_at=datetime.now(timezone.utc) - timedelta(hours=9))
        db.add(run)
        db.commit()
        syncsvc.tick(db)
        db.commit()
        db.refresh(run)
        assert run.status == "interrupted"
