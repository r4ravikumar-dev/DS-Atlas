from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....core.exceptions import Conflict, NotFound
from ....core.security import hash_password
from ....database.session import get_db
from ....models import AuditEvent, DuplicateGroup, Job, User
from ....repositories import paginate
from ....schemas import (AuditEventOut, ConfigOut, ConfigUpdate, Item, Page, ReviewItemOut, ReviewResolve, UserCreate, UserOut, UserUpdate)
from ....services import settings_service
from ....services.audit import audit
from ...deps import PageParams, Principal, page_params, require
from ..common import ERRORS, page_out

router = APIRouter(tags=["administration"], responses=ERRORS)


@router.get("/admin/users", response_model=Page[UserOut], dependencies=[Depends(require("admin:users"))])
def users(pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    rows, total = paginate(db, select(User).order_by(User.created_at), pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.post("/admin/users", response_model=Item[UserOut], status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, p: Principal = Depends(require("admin:users")), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.email) == body.email.lower())):
        raise Conflict("A user with this email already exists.")
    u = User(email=body.email.lower(), name=body.name, password_hash=hash_password(body.password), role=body.role)
    db.add(u)
    db.flush()
    audit(db, p.id, "user.create", "user", u.id, role=u.role)
    db.commit()
    return {"data": u}


@router.patch("/admin/users/{user_id}", response_model=Item[UserOut])
def update_user(user_id: uuid.UUID, body: UserUpdate, p: Principal = Depends(require("admin:users")), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise NotFound("User not found.")
    ch = body.model_dump(exclude_none=True)
    if u.id == p.id and (ch.get("role", "admin") != "admin" or ch.get("is_active") is False):
        raise Conflict("You cannot demote or deactivate your own account.")
    for k, v in ch.items():
        setattr(u, k, v)
    audit(db, p.id, "user.update", "user", u.id, changes=ch)
    db.commit()
    return {"data": u}


@router.get("/admin/audit-events", response_model=Page[AuditEventOut], dependencies=[Depends(require("admin:audit"))])
def audit_events(action: str | None = Query(None, max_length=100), pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    rows, total = paginate(db, stmt.order_by(AuditEvent.ts.desc()), pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.get("/admin/configuration", response_model=Item[ConfigOut], dependencies=[Depends(require("admin:config"))])
def get_config(db: Session = Depends(get_db)):
    return {"data": settings_service.get_config(db)}


@router.patch("/admin/configuration", response_model=Item[ConfigOut])
def patch_config(body: ConfigUpdate, p: Principal = Depends(require("admin:config")), db: Session = Depends(get_db)):
    changes = body.model_dump(exclude_none=True)
    cfg = settings_service.update_config(db, changes, p.id)
    audit(db, p.id, "config.update", "config", None, keys=sorted(changes))
    db.commit()
    return {"data": cfg}


@router.get("/admin/job-health", dependencies=[Depends(require("admin:config"))])
def job_health(db: Session = Depends(get_db)):
    by_status = dict(db.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    stale = db.scalar(select(func.count()).select_from(Job).where(Job.status == "running", Job.heartbeat_at < func.now() - func.make_interval(0, 0, 0, 0, 0, 10))) or 0
    oldest = db.scalar(select(func.min(Job.created_at)).where(Job.status == "queued"))
    return {"data": {"by_status": by_status, "stale_running": stale, "oldest_queued_at": oldest}}


@router.get("/admin/integrations/github", dependencies=[Depends(require("admin:config"))], summary="GitHub auth & rate-limit diagnostics (no secrets)")
def github_diag():
    from ....services.github_integration import diagnostics
    return {"data": diagnostics()}


@router.get("/review-queue", response_model=Page[ReviewItemOut], dependencies=[Depends(require("read"))], summary="Duplicate candidates & conflicts")
def review_queue(kind: str | None = Query(None, max_length=50), review_status: str = Query("open", pattern="^(open|resolved|dismissed|all)$"),
                 pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    stmt = select(DuplicateGroup)
    if kind:
        stmt = stmt.where(DuplicateGroup.kind == kind)
    if review_status != "all":
        stmt = stmt.where(DuplicateGroup.review_status == review_status)
    rows, total = paginate(db, stmt.order_by(DuplicateGroup.kind, DuplicateGroup.key), pp.page, pp.page_size)
    return page_out([r[0] for r in rows], total, pp.page, pp.page_size)


@router.post("/review-queue/auto-resolve", status_code=202, summary="Queue the evidence-based resolver (followed by a rebuild)")
def auto_resolve(p: Principal = Depends(require("review:resolve")), db: Session = Depends(get_db)):
    from ....services import jobs as jobsvc
    job = jobsvc.enqueue(db, "review", created_by=p.id, priority=120)
    build = jobsvc.enqueue(db, "build", params={"after": [str(job.id)]}, created_by=p.id, priority=200)
    audit(db, p.id, "review.auto_resolve", "job", job.id)
    db.commit()
    return {"data": {"job_ids": [job.id, build.id]}}


@router.get("/review-queue/{item_id}/decisions", dependencies=[Depends(require("read"))], summary="Decision history for a review item")
def decisions(item_id: int, db: Session = Depends(get_db)):
    from ....models import ReviewDecision
    g = db.get(DuplicateGroup, item_id)
    if not g:
        raise NotFound("Review item not found.")
    rows = db.scalars(select(ReviewDecision).where(ReviewDecision.review_key == g.key).order_by(ReviewDecision.id.desc()).limit(20)).all()
    return {"data": [{"id": r.id, "decision": r.decision, "confidence": r.confidence, "method": r.method, "rationale": r.rationale, "evidence": r.evidence,
                      "canonical_key": r.canonical_key, "related_keys": r.related_keys, "decided_by": r.decided_by, "created_at": r.created_at} for r in rows]}


@router.patch("/review-queue/{item_id}", response_model=Item[ReviewItemOut])
def resolve(item_id: int, body: ReviewResolve, p: Principal = Depends(require("review:resolve")), db: Session = Depends(get_db)):
    g = db.get(DuplicateGroup, item_id)
    if not g:
        raise NotFound("Review item not found.")
    from ....models import ReviewDecision
    g.review_status, g.resolution_note, g.resolved_by = body.review_status, body.resolution_note, p.id
    d = ReviewDecision(review_key=g.key, item_kind=g.kind, decision=f"human_{body.review_status}", canonical_key=None, related_keys=[],
                       confidence="high", method="human review", rationale=body.resolution_note or f"Marked {body.review_status} by reviewer",
                       evidence=[], original_item=g.details, decided_by=str(p.id))
    db.add(d)
    db.flush()
    g.decision_id = d.id
    audit(db, p.id, "review.resolve", "duplicate_group", g.id, status=body.review_status)
    db.commit()
    return {"data": g}
