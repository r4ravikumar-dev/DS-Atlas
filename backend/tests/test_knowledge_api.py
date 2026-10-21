"""Read APIs: pagination, filters, search, detail/relationship endpoints, comparisons and exports."""
import pytest

from app.database.session import SessionLocal
from app.models import Component, DesignSystem
from sqlalchemy import select


def test_pagination_meta(client, as_viewer, built_kb):
    r = client.get("/api/v1/components?page=1&page_size=1", headers=as_viewer).json()
    assert r["meta"]["page_size"] == 1 and r["meta"]["total_items"] >= 1 and len(r["data"]) == 1
    assert r["meta"]["total_pages"] == r["meta"]["total_items"]


def test_system_filters_and_detail(client, as_viewer, built_kb):
    r = client.get("/api/v1/design-systems", params={"q": "fixture"}, headers=as_viewer).json()
    assert any(x["name"] == "Fixture UI" for x in r["data"])
    sid = next(x["id"] for x in r["data"] if x["name"] == "Fixture UI")
    d = client.get(f"/api/v1/design-systems/{sid}", headers=as_viewer).json()["data"]
    assert d["verification_status"] in ("verified", "partially_verified", "unverified") and d["source_keys"] == ["FX1"]
    comps = client.get(f"/api/v1/design-systems/{sid}/components", headers=as_viewer).json()
    assert comps["meta"]["total_items"] >= 1
    assert client.get("/api/v1/design-systems/999999", headers=as_viewer).status_code == 404


def test_component_detail_and_related(client, as_viewer, built_kb):
    cid = client.get("/api/v1/components", params={"family": "Dialog", "library": "Fixture UI"}, headers=as_viewer).json()["data"][0]["id"]
    d = client.get(f"/api/v1/components/{cid}", headers=as_viewer).json()["data"]
    assert [p["name"] for p in d["props"]] == ["open", "defaultOpen", "onOpenChange"]
    assert d["keyboard"][0]["keys"] == "Escape" and d["interpretation_note"]
    ev = client.get(f"/api/v1/components/{cid}/evidence", headers=as_viewer).json()["data"]
    assert ev and ev[0]["url"] == "https://fixture.example/docs/dialog"
    assert client.get(f"/api/v1/components/{cid}/related-components", headers=as_viewer).status_code == 200


def test_tokens_filters_and_references(client, as_viewer, built_kb):
    r = client.get("/api/v1/tokens", params={"system": "Fixture UI", "type": "color", "has_alias": "true"}, headers=as_viewer).json()
    tok = r["data"][0]
    assert tok["name"] == "--fx-primary" and tok["raw_value"] == "var(--fx-brand)"
    refs = client.get(f"/api/v1/tokens/{tok['id']}/references", headers=as_viewer).json()["data"]
    assert refs[0]["name"] == "--fx-brand"
    deps = client.get(f"/api/v1/tokens/{refs[0]['id']}/dependents", headers=as_viewer).json()["data"]
    assert deps[0]["name"] == "--fx-primary"


def test_guidelines_and_search(client, as_viewer, built_kb):
    g = client.get("/api/v1/guidelines", params={"q": "focus", "category": "C07"}, headers=as_viewer).json()
    assert g["meta"]["total_items"] >= 1
    s = client.get("/api/v1/search", params={"q": "fixture dialog"}, headers=as_viewer).json()
    assert s["meta"]["total_items"] >= 1 and any(h["type"] == "component" for h in s["data"])
    fallback = client.get("/api/v1/search", params={"q": "dialog zzzznotaword"}, headers=as_viewer).json()
    assert fallback["meta"]["facets"]["_match_mode"] == "any" and fallback["meta"]["total_items"] >= 1
    assert client.get("/api/v1/search", params={"q": ""}, headers=as_viewer).status_code == 422


def test_comparisons(client, as_researcher, as_viewer, built_kb):
    with SessionLocal() as s:
        cid = s.scalar(select(Component.id).where(Component.name == "Dialog", Component.library == "Fixture UI"))
        other = s.scalar(select(Component.id).where(Component.id != cid))
        sys_id = s.scalar(select(DesignSystem.id).limit(1))
    body = {"name": "FIXTURE comparison", "kind": "components", "item_ids": [cid, other]}
    assert client.post("/api/v1/comparisons", json=body, headers=as_viewer).status_code == 403
    r = client.post("/api/v1/comparisons", json=body, headers=as_researcher)
    assert r.status_code == 201
    res = r.json()["data"]["result"]
    assert res["rows"]["state"]["State props"][0]["status"] == "documented"
    assert {c["status"] for row in res["rows"].values() for cells in row.values() for c in cells} <= {"documented", "not_documented", "not_applicable"}
    bad = client.post("/api/v1/comparisons", json={**body, "dimensions": ["nope"]}, headers=as_researcher)
    assert bad.status_code == 422
    missing = client.post("/api/v1/comparisons", json={"name": "x", "kind": "systems", "item_ids": [sys_id, 99999999]}, headers=as_researcher)
    assert missing.status_code == 422


@pytest.mark.parametrize("fmt", ["csv", "jsonl", "xlsx", "bundle"])
def test_export_generation_and_protected_download(client, as_researcher, as_viewer, built_kb, fmt):
    from app.models import Job
    from app.services import jobs as jobsvc
    from app.workers.main import run_export_job
    r = client.post("/api/v1/export-jobs", json={"format": fmt, "resource": "components" if fmt != "bundle" else "all"}, headers=as_researcher)
    assert r.status_code == 202
    jid = r.json()["data"]["job_ids"][0]
    with SessionLocal() as s:
        job = jobsvc.claim(s, "test-worker", ["export"])
        s.expunge(job)
    run_export_job(job)
    st = client.get(f"/api/v1/export-jobs/{jid}", headers=as_researcher).json()["data"]
    assert st["status"] == "succeeded" and st["result"]["size_bytes"] > 0
    assert client.get(f"/api/v1/export-jobs/{jid}/download").status_code == 401
    assert client.get(f"/api/v1/export-jobs/{jid}/download", headers=as_viewer).status_code == 401
    dl = client.get(f"/api/v1/export-jobs/{jid}/download", headers=as_researcher)
    assert dl.status_code == 200 and "attachment" in dl.headers["content-disposition"]
    link = client.post(f"/api/v1/export-jobs/{jid}/download-link", headers=as_researcher).json()["data"]["url"]
    assert client.get(link).status_code == 200  # signed, short-lived token
    assert client.get(link.replace("token=", "token=x")).status_code == 401
