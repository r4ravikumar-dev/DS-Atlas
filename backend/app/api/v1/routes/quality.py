"""Data-quality reporting and the add-a-source workflow (duplicate check → attach or create → crawl → rebuild → verify)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ....core.exceptions import AppError, Conflict, NotFound
from ....database.session import get_db
from ....models import DesignSystem, DuplicateGroup, IdentityLink, Job, Source, SystemResource
from ....scrapers.dskb.core import slugify
from ....scrapers.dskb.pipeline import site_key
from ....schemas import IntakeCheck, IntakeCheckOut, IntakeOut, IntakeRequest, Item, ResourceOut
from ....services import jobs as jobsvc
from ....services import resources as ressvc
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, page_out
from .systems import add_manual_resource

router = APIRouter(tags=["data-quality"], responses=ERRORS)

ISSUES: dict[str, str] = {
    "duplicate_candidates": "Possible duplicate systems awaiting a decision",
    "missing_official_url": "Systems without any official website or documentation link",
    "invalid_links": "Links that returned 404/410/5xx when checked, or were flagged by the administrator",
    "unverified_github": "Systems whose repository links are all unverified (listed by directories only)",
    "figma_not_found": "Official page checked, no Figma file linked (absence — not an error)",
    "figma_unchecked": "Figma availability unknown (official page not checked yet)",
    "orphaned_records": "Records that point at a system (or must belong to one) but are not attached to a canonical system",
    "extraction_failures": "Failed crawl/build/verification jobs and Storybook projects that could not be enumerated",
    "needs_recrawl": "Sources whose last successful crawl is older than 30 days, failed, or never ran",
}


def _missing_official():
    return ~select(SystemResource.id).where(SystemResource.system_id == DesignSystem.id,
                                            SystemResource.resource_type.in_(["official_website", "official_documentation"]),
                                            SystemResource.verification_status != "invalid").exists()


def _figma_checked(checked: bool):
    """Systems whose primary official page was fetched successfully by the verifier (checked=True) or not (False), with no figma link."""
    no_figma = ~select(SystemResource.id).where(SystemResource.system_id == DesignSystem.id, SystemResource.resource_type == "figma_file",
                                                SystemResource.verification_status != "invalid").exists()
    ok_page = select(SystemResource.id).where(SystemResource.system_id == DesignSystem.id, SystemResource.is_primary.is_(True),
                                              SystemResource.resource_type.in_(["official_website", "official_documentation"]),
                                              SystemResource.last_checked_at.is_not(None), SystemResource.http_status.between(200, 399)).exists()
    return no_figma & (ok_page if checked else ~ok_page)


def _unverified_github():
    has = select(SystemResource.id).where(SystemResource.system_id == DesignSystem.id, SystemResource.resource_type == "github_repository",
                                          SystemResource.verification_status == "unverified").exists()
    verified = select(SystemResource.id).where(SystemResource.system_id == DesignSystem.id, SystemResource.resource_type == "github_repository",
                                               SystemResource.verification_status == "verified").exists()
    return has & ~verified


def _count_systems(db: Session, cond) -> int:
    return db.scalar(select(func.count()).select_from(DesignSystem).where(cond)) or 0


LINKED = """EXISTS (SELECT 1 FROM entity_relationships e JOIN records t ON t.id = e.to_record_id
                    WHERE e.from_record_id = {tbl}.record_id AND e.type IN ('documented_by_system','token_of','part_of','foundation_of')
                      AND t.system_id IS NOT NULL)"""


def orphan_counts(db: Session) -> dict[str, int]:
    """Broken = a row that points at a system record (or must belong to a system) yet is not attached to a canonical system.
    System-agnostic records (cross-system checklists, specifications, overviews) are not broken."""
    q = lambda sql: db.scalar(text(sql)) or 0  # noqa: E731
    return {
        "components_unattached_despite_system_link": q(f"SELECT count(*) FROM components WHERE system_id IS NULL AND {LINKED.format(tbl='components')}"),
        "tokens_unattached_despite_system_link": q(f"SELECT count(*) FROM design_tokens WHERE system_id IS NULL AND {LINKED.format(tbl='design_tokens')}"),
        "guidelines_unattached_despite_system_link": q(f"SELECT count(*) FROM guidelines WHERE system_id IS NULL AND {LINKED.format(tbl='guidelines')}"),
        "resources_without_system": q("SELECT count(*) FROM system_resources WHERE system_id IS NULL"),
        "storybook_projects_without_system": q("SELECT count(*) FROM storybook_projects WHERE system_key IS NULL OR NOT EXISTS "
                                               "(SELECT 1 FROM design_systems d WHERE d.key = storybook_projects.system_key)"),
        "evidence_without_system": q("SELECT count(*) FROM attribute_evidence WHERE system_id IS NULL"),
        "system_records_without_system": q("SELECT count(*) FROM records WHERE record_type = 'system' AND NOT is_stale AND system_id IS NULL"),
    }


def _stale_sources(db: Session):
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    return select(Source).where(Source.is_paused.is_(False)).where(
        (Source.last_success_at.is_(None)) | (Source.last_success_at < cutoff) | (Source.status.not_in(["inspected", "inspected_partial"])))


@router.get("/quality", dependencies=[Depends(require("read"))], summary="Data-quality summary (counts per issue type)")
def quality_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    failed_jobs = db.scalar(select(func.count()).select_from(Job).where(Job.status == "failed", Job.created_at >= since)) or 0
    sb_fail = db.scalar(text("SELECT count(*) FROM storybook_projects WHERE status <> 'indexed'")) or 0
    orphans = orphan_counts(db)
    counts = {
        "duplicate_candidates": db.scalar(select(func.count()).select_from(DuplicateGroup).where(
            DuplicateGroup.review_status == "open", DuplicateGroup.kind == "possible_duplicate_system")) or 0,
        "missing_official_url": _count_systems(db, _missing_official()),
        "invalid_links": db.scalar(select(func.count()).select_from(SystemResource).where(SystemResource.verification_status == "invalid",
                                                                                           SystemResource.system_id.is_not(None))) or 0,
        "unverified_github": _count_systems(db, _unverified_github()),
        "figma_not_found": _count_systems(db, _figma_checked(True)),
        "figma_unchecked": _count_systems(db, _figma_checked(False)),
        "orphaned_records": sum(orphans.values()),
        "extraction_failures": failed_jobs + sb_fail,
        "needs_recrawl": db.scalar(select(func.count()).select_from(_stale_sources(db).subquery())) or 0,
    }
    return {"data": {"counts": counts, "labels": ISSUES, "orphans": orphans, "failed_jobs_30d": failed_jobs, "storybook_not_extracted": sb_fail,
                     "systems_total": db.scalar(select(func.count()).select_from(DesignSystem)) or 0,
                     "figma_verified_systems": _count_systems(db, select(SystemResource.id).where(
                         SystemResource.system_id == DesignSystem.id, SystemResource.resource_type == "figma_file",
                         SystemResource.verification_status == "verified").exists())}}


@router.get("/quality/issues", dependencies=[Depends(require("read"))], summary="Items for one data-quality issue type (paginated)")
def quality_issues(kind: str = Query(..., pattern="^(" + "|".join(ISSUES) + ")$"), pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    def systems(cond):
        stmt = select(DesignSystem).where(cond).order_by(DesignSystem.source_count.desc(), DesignSystem.name)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.offset(pp.offset).limit(pp.page_size)).all()
        return page_out([{"kind": "system", "id": s.id, "title": s.name, "subtitle": s.organization, "detail": f"{s.source_count} source(s)",
                          "href": f"/platform/systems/{s.id}"} for s in rows], total, pp.page, pp.page_size)

    if kind == "missing_official_url":
        return systems(_missing_official())
    if kind == "unverified_github":
        return systems(_unverified_github())
    if kind in ("figma_not_found", "figma_unchecked"):
        return systems(_figma_checked(kind == "figma_not_found"))
    if kind == "duplicate_candidates":
        stmt = select(DuplicateGroup).where(DuplicateGroup.review_status == "open", DuplicateGroup.kind == "possible_duplicate_system").order_by(DuplicateGroup.id)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.offset(pp.offset).limit(pp.page_size)).all()
        return page_out([{"kind": "review", "id": g.id, "title": ", ".join(e.get("name", "?") for e in (g.details or {}).get("entities", [])),
                          "subtitle": g.resolution or "not evaluated", "detail": (g.details or {}).get("reason"), "href": "/platform/review?kind=possible_duplicate_system"}
                         for g in rows], total, pp.page, pp.page_size)
    if kind == "invalid_links":
        stmt = (select(SystemResource, DesignSystem.name).join(DesignSystem, DesignSystem.id == SystemResource.system_id)
                .where(SystemResource.verification_status == "invalid").order_by(DesignSystem.name))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.execute(stmt.offset(pp.offset).limit(pp.page_size)).all()
        return page_out([{"kind": "resource", "id": r.id, "title": f"{n} — {r.resource_type.replace('_', ' ')}", "subtitle": r.url,
                          "detail": r.evidence_note or (f"HTTP {r.http_status}" if r.http_status else None), "href": f"/platform/systems/{r.system_id}"}
                         for r, n in rows], total, pp.page, pp.page_size)
    if kind == "orphaned_records":
        items = [{"kind": "count", "id": i, "title": k.replace("_", " "), "subtitle": None, "detail": str(v), "href": None}
                 for i, (k, v) in enumerate(orphan_counts(db).items())]
        return page_out(items, len(items), 1, max(1, len(items)))
    if kind == "extraction_failures":
        since = datetime.now(timezone.utc) - timedelta(days=30)
        jobs = db.scalars(select(Job).where(Job.status == "failed", Job.created_at >= since).order_by(Job.created_at.desc()).limit(100)).all()
        sb = db.execute(text("SELECT id, title, status, limitation FROM storybook_projects WHERE status <> 'indexed' ORDER BY title")).all()
        items = [{"kind": "job", "id": str(j.id), "title": f"{j.kind} job failed", "subtitle": (j.error or "")[:200], "detail": j.created_at.isoformat(),
                  "href": f"/platform/jobs/{j.id}"} for j in jobs]
        items += [{"kind": "storybook", "id": i, "title": f"Storybook: {t}", "subtitle": st, "detail": (lim or "")[:240], "href": "/platform/storybook"}
                  for i, t, st, lim in sb]
        return page_out(items[pp.offset:pp.offset + pp.page_size], len(items), pp.page, pp.page_size)
    if kind == "needs_recrawl":
        stmt = _stale_sources(db).order_by(Source.key)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.offset(pp.offset).limit(pp.page_size)).all()
        return page_out([{"kind": "source", "id": s.id, "title": f"{s.key} · {s.name}", "subtitle": s.status,
                          "detail": f"last success {s.last_success_at:%Y-%m-%d}" if s.last_success_at else "never succeeded",
                          "href": f"/platform/sources/{s.id}"} for s in rows], total, pp.page, pp.page_size)
    raise NotFound("Unknown issue type.")


# ───────────────────────────── intake ─────────────────────────────

def _candidates(db: Session, url: str, name: str | None) -> list[dict[str, Any]]:
    from ....services.review_resolver import norm_name
    out: dict[int, dict[str, Any]] = {}
    rtype = ressvc.classify(url)
    canon = ressvc.canon(rtype, url)
    h = ressvc.host(url)
    sk = site_key(url)

    def add(s: DesignSystem, match: str, detail: str, rank: int):
        cur = out.get(s.id)
        if not cur or cur["_rank"] < rank:
            out[s.id] = {"system_id": s.id, "name": s.name, "organization": s.organization, "match": match, "detail": detail, "_rank": rank}

    for r, s in db.execute(select(SystemResource, DesignSystem).join(DesignSystem, DesignSystem.id == SystemResource.system_id)
                           .where(SystemResource.canonical_url == canon)):
        add(s, "same_url", f"Already recorded as {r.resource_type.replace('_', ' ')} of this system.", 5)
    repo = ressvc.github_repo(url)
    if repo:
        owner = ressvc.github_owner(url)
        for r, s in db.execute(select(SystemResource, DesignSystem).join(DesignSystem, DesignSystem.id == SystemResource.system_id)
                               .where(SystemResource.resource_type == "github_repository", SystemResource.canonical_url.like(f"https://{owner}/%"))):
            add(s, "same_repository_owner", f"Repository owner {owner} also publishes {r.canonical_url}.", 3)
    elif sk:
        key = f"dsys:{slugify(sk)}"
        s = db.scalar(select(DesignSystem).where(DesignSystem.key == key))
        if s:
            add(s, "same_site", f"Same documentation site ({sk}); a crawl would resolve to this system.", 5)
        for r, s in db.execute(select(SystemResource, DesignSystem).join(DesignSystem, DesignSystem.id == SystemResource.system_id)
                               .where(SystemResource.canonical_url.like(f"https://{h}%") | SystemResource.canonical_url.like(f"https://www.{h}%"))
                               .limit(20)):
            add(s, "same_host", f"{r.resource_type.replace('_', ' ')} on the same host: {r.url}", 4)
    n = norm_name(name) if name else None
    if n:
        for s in db.scalars(select(DesignSystem).where(func.lower(DesignSystem.name).contains(n.split(" ")[0])).limit(200)):
            if norm_name(s.name) == n:
                add(s, "same_name", "Same normalized name.", 2)
    return sorted(out.values(), key=lambda c: -c.pop("_rank"))


@router.post("/intake/check", response_model=Item[IntakeCheckOut], dependencies=[Depends(require("source:create"))],
             summary="Before adding a URL: find likely existing canonical systems")
def intake_check(body: IntakeCheck, db: Session = Depends(get_db)):
    rtype = ressvc.classify(body.url)
    if rtype == "additional_resource" and not ressvc.host(body.url).endswith("figma.com"):
        rtype = "official_documentation" if urlparse(body.url).path.strip("/") else "official_website"
    sk = site_key(body.url)
    return {"data": {"url": body.url, "canonical_url": ressvc.canon(rtype, body.url), "suggested_type": rtype,
                     "predicted_key": f"dsys:{slugify(sk)}" if sk and not ressvc.github_repo(body.url) else None,
                     "candidates": _candidates(db, body.url, body.name)}}


@router.post("/intake", response_model=Item[IntakeOut], status_code=201, summary="Attach a URL to a system or create a separate system, then crawl")
def intake(body: IntakeRequest, p: Principal = Depends(require("source:create")), db: Session = Depends(get_db)):
    if bool(body.system_id) == bool(body.new_system):
        raise AppError("Provide exactly one of system_id (attach) or new_system (create).", code="VALIDATION_ERROR", status_code=422)
    job_ids: list = []
    if body.system_id:
        s = db.get(DesignSystem, body.system_id)
        if not s:
            raise NotFound("Design system not found.")
        key, sid, name, org = s.key, s.id, s.name, s.organization
    else:
        cands = _candidates(db, body.url, body.new_system.name)
        strong = [c for c in cands if c["match"] in ("same_url", "same_site", "same_host", "same_name", "same_repository_owner")]
        unresolved = [c for c in strong if c["system_id"] not in set(body.separate_from)]
        if unresolved:
            raise Conflict("Likely existing system(s) found. Attach the URL to one of them, or confirm they are different by listing them in separate_from.",
                           details=[{"system_id": c["system_id"], "name": c["name"], "match": c["match"], "reason": c["detail"]} for c in unresolved])
        if any(c["match"] in ("same_url", "same_site") for c in strong):
            raise Conflict("This exact URL or documentation site already belongs to a canonical system; a crawl would merge into it. Attach instead.")
        sk = site_key(body.url) if not ressvc.github_repo(body.url) else None
        if not sk:
            raise AppError("A new system needs its official website or documentation URL (not a repository or Figma link) as the first source.",
                           code="VALIDATION_ERROR", status_code=422)
        key, sid, name, org = f"dsys:{slugify(sk)}", None, body.new_system.name, body.new_system.organization
        pending = db.scalar(select(SystemResource).where(SystemResource.system_key == key, SystemResource.system_id.is_(None)))
        bound = db.scalar(select(Source).where(Source.system_key == key))
        if pending or bound:
            raise Conflict(f"This system was already submitted ({key}) and is waiting for its crawl and rebuild; check Crawl jobs.")
        for other in body.separate_from:
            o = db.get(DesignSystem, other)
            if o:
                db.add(IdentityLink(from_key=key, to_key=o.key, relation="distinct_from",
                                    evidence=[{"type": "admin_decision", "user_id": str(p.id), "rationale": "Administrator confirmed a separate system at intake."}]))
    res = add_manual_resource(db, key, sid, body.resource_type, body.url, verified=body.verified,
                              note="Added and confirmed by the administrator." if body.verified else None, user_id=p.id)
    source_id = None
    if body.crawl and body.resource_type in ("official_website", "official_documentation"):
        src = db.scalar(select(Source).where(Source.canonical_url == ressvc.canon("official_documentation", body.url)))
        if src is None:
            n = (db.scalar(text("SELECT count(*) FROM sources WHERE origin = 'official'")) or 0) + 1
            skey = f"O{n:02d}"
            while db.scalar(select(Source.id).where(Source.key == skey)):
                n += 1
                skey = f"O{n:02d}"
            src = Source(key=skey, name=f"{name} — official documentation", url=body.url, canonical_url=ressvc.canon("official_documentation", body.url),
                         domain=urlparse(body.url).hostname or "", source_type="documentation", adapter="official_docs", origin="official", system_key=key,
                         crawl_limits={"system_name": name, "organization": org, "max_pages": 45, "max_depth": 3})
            db.add(src)
            db.flush()
        elif src.system_key != key:
            raise Conflict(f"This URL is already registered as source {src.key} for another system.")
        from ....services.evidence_fetch import approve_hosts
        from ....services import settings_service
        hosts = approve_hosts([body.url])
        cfg = settings_service.get_config(db)
        if not hosts <= set(cfg["approved_domains"]):
            settings_service.update_config(db, {"approved_domains": sorted(set(cfg["approved_domains"]) | hosts)})
            audit(db, p.id, "config.approve_domains", "config", None, domains=sorted(hosts), reason="administrator intake")
        crawl = jobsvc.enqueue(db, "crawl", source_id=src.id, created_by=p.id, params={"reason": "intake"})
        build = jobsvc.enqueue(db, "build", params={"after": [str(crawl.id)]}, created_by=p.id, priority=200)
        verify = jobsvc.enqueue(db, "verify_resources", params={"after": [str(build.id)], "system_keys": [key]}, created_by=p.id, priority=210)
        job_ids, source_id = [crawl.id, build.id, verify.id], src.id
    audit(db, p.id, "intake.add", "system_resource", res.id, system=key, url=body.url, type=body.resource_type, created_system=bool(body.new_system),
          separate_from=body.separate_from, jobs=[str(j) for j in job_ids])
    db.commit()
    db.refresh(res)
    return {"data": {"system_key": key, "system_id": sid, "resource": ResourceOut.model_validate(res), "source_id": source_id, "job_ids": job_ids}}


@router.post("/resources/verify", status_code=202, summary="Queue verification of official pages (repository / Figma / Storybook discovery)")
def queue_verify(system_id: int | None = None, p: Principal = Depends(require("crawl:start")), db: Session = Depends(get_db)):
    job = jobsvc.enqueue(db, "verify_resources", params={"system_ids": [system_id]} if system_id else {}, created_by=p.id, priority=150)
    audit(db, p.id, "resources.verify", "job", job.id, system_id=system_id)
    db.commit()
    return {"data": {"job_ids": [job.id]}}
