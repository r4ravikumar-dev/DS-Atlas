"""Job state machine, idempotent ingestion, stale marking, build projections and the crawl worker."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.exceptions import Conflict
from app.database.session import SessionLocal
from app.models import Component, ComponentProp, DesignSystem, DesignToken, DiscoveredUrl, Guideline, Job, Record, Source, TokenReference
from app.services import ingest, jobs as jobsvc
from conftest import fixture_result


def test_job_lifecycle_and_conflicts(fixture_source):
    with SessionLocal() as s:
        j = jobsvc.enqueue(s, "crawl", source_id=fixture_source)
        s.commit()
        with pytest.raises(Conflict):
            jobsvc.enqueue(s, "crawl", source_id=fixture_source)
        s.rollback()
        claimed = jobsvc.claim(s, "test-worker", ["crawl"])
        assert claimed and claimed.id == j.id and claimed.status == "running" and claimed.attempts == 1
        assert jobsvc.claim(s, "other-worker", ["crawl"]) is None  # nothing else queued
        cancelled = jobsvc.heartbeat(s, j.id, urls_processed=5)
        assert cancelled is False
        jobsvc.finish(s, j.id, "succeeded", records_extracted=3)
        done = s.get(Job, j.id)
        s.refresh(done)
        assert done.status == "succeeded" and done.urls_processed == 5 and done.finished_at
        with pytest.raises(Conflict):
            jobsvc.cancel(s, j.id)
        with pytest.raises(Conflict):
            jobsvc.retry(s, j.id, None)


def test_cancel_queued_and_retry_failed(fixture_source):
    with SessionLocal() as s:
        j = jobsvc.enqueue(s, "build")
        jobsvc.cancel(s, j.id)
        s.commit()
        assert s.get(Job, j.id).status == "cancelled"
        r = jobsvc.retry(s, j.id, None)
        s.commit()
        assert r.retry_of == j.id and r.status == "queued"
        jobsvc.cancel(s, r.id)
        s.commit()


def test_stale_running_job_is_recovered():
    with SessionLocal() as s:
        j = jobsvc.enqueue(s, "export", params={"format": "csv", "resource": "sources"})
        s.commit()
        jobsvc.claim(s, "dead-worker", ["export"])
        s.query(Job).filter(Job.id == j.id).update({"heartbeat_at": datetime.now(timezone.utc) - timedelta(hours=1)})
        s.commit()
        assert jobsvc.recover_stale(s, 300) == 1
        fresh = s.get(Job, j.id)
        s.refresh(fresh)
        assert fresh.status == "queued" and fresh.phase == "retry_scheduled"
        jobsvc.cancel(s, j.id)
        s.commit()


def test_ingest_is_idempotent_and_marks_stale(built_kb, fixture_source):
    with SessionLocal() as s:
        src = s.get(Source, fixture_source)
        before = s.scalar(select(func.count()).select_from(Record).where(Record.source_id == src.id))
        job = jobsvc.enqueue(s, "build")  # any job id works as the observation marker
        res = ingest.ingest(s, src, job.id, fixture_result(src.key, 2))  # variant 2 drops the 'Legacy' component
        jobsvc.cancel(s, job.id)
        s.commit()
        after = s.scalar(select(func.count()).select_from(Record).where(Record.source_id == src.id))
        assert after == before  # upserted, not duplicated
        assert res["records_marked_stale"] == 1
        legacy = s.scalar(select(Record).where(Record.record_key == "cmp:fx1:legacy"))
        assert legacy.is_stale is True
        dialog = s.scalar(select(Record).where(Record.record_key == "cmp:fx1:dialog"))
        assert dialog.is_stale is False and dialog.source_version == "0.2.0"
        assert src.status == "inspected" and src.last_success_at is not None


def test_build_projections(built_kb):
    assert built_kb["validation_issues"] == 0
    with SessionLocal() as s:
        sysrow = s.scalar(select(DesignSystem).where(DesignSystem.key == "dsys:fixture-example"))
        assert sysrow and sysrow.name == "Fixture UI" and sysrow.organization == "Fixture Org"
        comp = s.scalar(select(Component).where(Component.name == "Dialog", Component.library == "Fixture UI"))
        assert comp.family == "Dialog" and comp.props_count == 3 and comp.keyboard_count == 1 and comp.system_id == sysrow.id
        names = s.scalars(select(ComponentProp.name).where(ComponentProp.component_id == comp.id).order_by(ComponentProp.position)).all()
        assert names == ["open", "defaultOpen", "onOpenChange"]
        primary = s.scalar(select(DesignToken).where(DesignToken.name == "--fx-primary"))
        assert primary.raw_value == "var(--fx-brand)" and primary.resolved_value == "#123456"  # raw preserved; resolved computed
        assert s.scalar(select(func.count()).select_from(TokenReference)) >= 1
        assert s.scalar(select(func.count()).select_from(Guideline).where(Guideline.title.like("Fixture%"))) == 1


def test_crawl_worker_persists_urls_records_and_status(fixture_source, monkeypatch):
    """Runs the real crawl handler with a FIXTURE adapter that emits fetch events through the engine listener."""
    from app.scrapers.dskb import core
    from app.workers import crawl as crawlmod

    def fake_adapter(seed):
        cb = core.FETCHER.listeners[seed["source_id"]]
        for i in range(3):
            resp = core.Response(f"https://fixture.example/p{i}", f"https://fixture.example/p{i}", 200, f"FIXTURE page {i}".encode(), {"content-type": "text/html"},
                                 core.now_iso(), False, core.sha256(f"FIXTURE page {i}".encode()))
            cb({"url": resp.url, "source_id": seed["source_id"], "parent": None, "depth": 1, "outcome": "fetched", "status": 200, "final_url": resp.url}, resp)
        cb({"url": "https://fixture.example/missing", "source_id": seed["source_id"], "outcome": "http_error", "status": 404}, None)
        return fixture_result(seed["source_id"], 2)

    monkeypatch.setitem(crawlmod.ADAPTERS, "generic", fake_adapter)
    with SessionLocal() as s:
        j = jobsvc.enqueue(s, "crawl", source_id=fixture_source)
        s.commit()
        job = jobsvc.claim(s, "test-worker", ["crawl"])
        s.expunge(job)
    crawlmod.run_crawl(job)
    with SessionLocal() as s:
        done = s.get(Job, j.id)
        assert done.status == "succeeded"
        assert done.urls_processed == 3 and done.error_count == 1 and done.records_extracted == 5
        urls = s.scalars(select(DiscoveredUrl).where(DiscoveredUrl.source_id == fixture_source)).all()
        assert {u.outcome for u in urls} >= {"fetched", "http_error"}
        assert all(u.raw_document_id for u in urls if u.outcome == "fetched")


def test_crawl_cancellation(fixture_source, monkeypatch):
    from app.scrapers.dskb import core
    from app.workers import crawl as crawlmod

    def slow_adapter(seed):
        cb = core.FETCHER.listeners[seed["source_id"]]
        for i in range(50):
            cb({"url": f"https://fixture.example/c{i}", "source_id": seed["source_id"], "outcome": "fetched", "status": 200}, None)
            cb.last_beat = 0  # force a heartbeat (and cancellation check) on every event
        return fixture_result(seed["source_id"], 2)

    monkeypatch.setitem(crawlmod.ADAPTERS, "generic", slow_adapter)
    with SessionLocal() as s:
        j = jobsvc.enqueue(s, "crawl", source_id=fixture_source)
        s.commit()
        job = jobsvc.claim(s, "test-worker", ["crawl"])
        s.query(Job).filter(Job.id == j.id).update({"cancel_requested": True})
        s.commit()
        s.expunge(job)
    crawlmod.run_crawl(job)
    with SessionLocal() as s:
        assert s.get(Job, j.id).status == "cancelled"
