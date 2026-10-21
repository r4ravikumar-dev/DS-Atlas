"""Invitation lifecycle: create → deliver → validate → email code → accept (atomic) ; resend / revoke / expire.

Security properties
* Token: 256-bit `secrets.token_urlsafe`; stored only as HMAC-SHA256(secret_key, token).
* Link carries the token in the URL fragment (`#token=…`), so it is not sent to servers, proxies, logs or Referer headers.
* Identity binding: acceptance requires a 6-digit code emailed to the invited address at acceptance time
  (forwarded links cannot be claimed without access to the mailbox). Codes are HMAC-stored, expire in 10 min, 5 attempts.
* Single use: acceptance is an atomic conditional UPDATE; replay, expiry and revocation are rejected uniformly.
* Unauthenticated responses never reveal whether an email address already has an account."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.exceptions import AppError, Conflict, NotFound
from ..core.security import hash_password
from ..models import Invitation, User
from . import email as mail
from .audit import audit

CODE_TTL = timedelta(minutes=10)
GENERIC_INVALID = "This invitation link is invalid, expired, or has already been used. Ask an administrator for a new invitation."


def _digest(value: str) -> str:
    return hmac.new(get_settings().secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def now() -> datetime:
    return datetime.now(timezone.utc)


def status_of(inv: Invitation) -> str:
    if inv.accepted_at:
        return "accepted"
    if inv.revoked_at:
        return "revoked"
    if inv.expires_at <= now():
        return "expired"
    return "pending"


def to_out(inv: Invitation) -> dict[str, Any]:
    return {"id": inv.id, "kind": inv.kind, "email": inv.email, "role": inv.role, "status": status_of(inv), "created_at": inv.created_at,
            "expires_at": inv.expires_at, "accepted_at": inv.accepted_at, "revoked_at": inv.revoked_at, "invited_by": inv.invited_by,
            "delivery_status": inv.delivery_status, "delivery_error": inv.delivery_error, "send_count": inv.send_count, "last_sent_at": inv.last_sent_at}


def _mask(email: str) -> str:
    local, _, domain = email.partition("@")
    return (local[:2] + "•" * max(1, len(local) - 2)) + "@" + domain


def _deliver(db: Session, inv: Invitation, token: str) -> None:
    s = get_settings()
    link = f"{s.app_base_url.rstrip('/')}/platform/invite#token={token}"
    subject = "You're invited to the Design Systems Research Platform" if inv.kind == "access" else "Reset your Design Systems Research Platform password"
    body = (f"You have been {'invited' if inv.kind == 'access' else 'sent a password reset'} for {inv.email}.\n\n"
            f"Open this link to continue (expires {inv.expires_at:%Y-%m-%d %H:%M} UTC):\n{link}\n\n"
            "You will also need a verification code that we send to this address when you open the link.\n"
            "If you did not expect this message you can ignore it.")
    inv.send_count += 1
    inv.last_sent_at = now()
    try:
        mail.send(inv.email, subject, body)
        inv.delivery_status, inv.delivery_error = "sent", None
    except mail.NotConfigured as e:
        inv.delivery_status, inv.delivery_error = "not_configured", str(e)
    except mail.DeliveryError as e:
        inv.delivery_status, inv.delivery_error = "failed", str(e)


def create(db: Session, *, email: str, role: str, invited_by: uuid.UUID | None, ttl_hours: int | None = None, kind: str = "access") -> Invitation:
    s = get_settings()
    email = email.strip().lower()
    ttl = min(ttl_hours or s.invitation_ttl_hours, s.invitation_max_ttl_hours)
    if kind == "access":
        if db.scalar(select(User.id).where(func.lower(User.email) == email)):
            raise Conflict("A user with this email already exists. Manage their role or access in Users.")
        pending = db.scalars(select(Invitation).where(Invitation.email == email, Invitation.kind == "access", Invitation.accepted_at.is_(None),
                                                      Invitation.revoked_at.is_(None), Invitation.expires_at > now())).all()
        for p in pending:  # one live invitation per address: supersede older ones
            p.revoked_at, p.revoked_by = now(), invited_by
    token = secrets.token_urlsafe(32)
    inv = Invitation(kind=kind, email=email, role=role, token_digest=_digest(token), invited_by=invited_by, expires_at=now() + timedelta(hours=ttl))
    db.add(inv)
    db.flush()
    _deliver(db, inv, token)
    audit(db, invited_by, f"invitation.{'create' if kind == 'access' else 'reset_create'}", "invitation", inv.id, email=email, role=role,
          ttl_hours=ttl, delivery=inv.delivery_status)
    return inv


def resend(db: Session, inv_id: uuid.UUID, actor: uuid.UUID) -> Invitation:
    inv = db.get(Invitation, inv_id)
    if not inv:
        raise NotFound("Invitation not found.")
    if status_of(inv) in ("accepted", "revoked"):
        raise Conflict(f"Invitation is {status_of(inv)}; create a new one instead.")
    token = secrets.token_urlsafe(32)  # rotate: the previous link stops working
    inv.token_digest = _digest(token)
    inv.expires_at = max(inv.expires_at, now() + timedelta(hours=get_settings().invitation_ttl_hours))
    inv.code_digest, inv.code_expires_at, inv.code_attempts = None, None, 0
    _deliver(db, inv, token)
    audit(db, actor, "invitation.resend", "invitation", inv.id, delivery=inv.delivery_status)
    return inv


def revoke(db: Session, inv_id: uuid.UUID, actor: uuid.UUID) -> Invitation:
    inv = db.get(Invitation, inv_id)
    if not inv:
        raise NotFound("Invitation not found.")
    if inv.accepted_at:
        raise Conflict("Invitation already accepted; revoke the user's access instead.")
    inv.revoked_at, inv.revoked_by = inv.revoked_at or now(), actor
    audit(db, actor, "invitation.revoke", "invitation", inv.id)
    return inv


def _live(db: Session, token: str, lock: bool = False) -> Invitation:
    if not token or len(token) > 200:
        raise AppError(GENERIC_INVALID, code="INVITATION_INVALID", status_code=400)
    q = select(Invitation).where(Invitation.token_digest == _digest(token))
    if lock:
        q = q.with_for_update()
    inv = db.scalar(q)
    if not inv or status_of(inv) != "pending":
        raise AppError(GENERIC_INVALID, code="INVITATION_INVALID", status_code=400)
    return inv


def validate(db: Session, token: str) -> dict[str, Any]:
    inv = _live(db, token)
    return {"kind": inv.kind, "email_hint": _mask(inv.email), "role": inv.role, "expires_at": inv.expires_at,
            "email_delivery": mail.transport_name() != "disabled"}


def send_code(db: Session, token: str) -> dict[str, Any]:
    inv = _live(db, token, lock=True)
    if inv.code_sent_count >= 5:
        raise AppError("Too many verification codes requested for this invitation. Ask an administrator to resend it.", code="RATE_LIMITED", status_code=429)
    code = f"{secrets.randbelow(10**6):06d}"
    inv.code_digest, inv.code_expires_at, inv.code_attempts = _digest(f"{inv.id}:{code}"), now() + CODE_TTL, 0
    inv.code_sent_count += 1
    try:
        mail.send(inv.email, "Your verification code", f"Your verification code is {code}. It expires in 10 minutes.\nIf you did not request it, ignore this email.")
    except mail.NotConfigured:
        raise AppError("Email delivery is not configured, so your address cannot be verified yet. Contact the administrator.", code="EMAIL_NOT_CONFIGURED", status_code=503)
    except mail.DeliveryError:
        raise AppError("We could not send the verification email. Try again later.", code="EMAIL_DELIVERY_FAILED", status_code=502)
    return {"sent_to": _mask(inv.email), "expires_in_seconds": int(CODE_TTL.total_seconds())}


def accept(db: Session, *, token: str, code: str, name: str, password: str) -> User:
    inv = _live(db, token, lock=True)  # row lock serializes concurrent attempts
    if not inv.code_digest or not inv.code_expires_at or inv.code_expires_at <= now():
        raise AppError("Request a verification code first (or the code expired).", code="CODE_REQUIRED", status_code=400)
    if inv.code_attempts >= 5:
        raise AppError("Too many incorrect codes. Request a new code.", code="CODE_LOCKED", status_code=429)
    if not hmac.compare_digest(inv.code_digest, _digest(f"{inv.id}:{code.strip()}")):
        inv.code_attempts += 1
        db.commit()
        raise AppError("The verification code is incorrect.", code="CODE_INVALID", status_code=400)
    if len(password) < 12:
        raise AppError("Password must be at least 12 characters.", code="VALIDATION_ERROR", status_code=422, details=[{"field": "password", "reason": "min length 12"}])
    # Atomic single-use consumption (also guards against races without the row lock)
    res = db.execute(update(Invitation).where(Invitation.id == inv.id, Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None),
                                              Invitation.expires_at > now()).values(accepted_at=now(), code_digest=None))
    if res.rowcount != 1:
        raise AppError(GENERIC_INVALID, code="INVITATION_INVALID", status_code=400)
    user = db.scalar(select(User).where(func.lower(User.email) == inv.email))
    if inv.kind == "access":
        if user:  # an account appeared meanwhile — do not merge silently
            raise AppError(GENERIC_INVALID, code="INVITATION_INVALID", status_code=400)
        user = User(email=inv.email, name=name.strip()[:200], password_hash=hash_password(password), role=inv.role, is_active=True, email_verified_at=now())
        db.add(user)
    else:
        if not user or not user.is_active:
            raise AppError(GENERIC_INVALID, code="INVITATION_INVALID", status_code=400)
        user.password_hash = hash_password(password)
        user.session_version += 1  # sign out every existing session
        user.email_verified_at = user.email_verified_at or now()
    db.flush()
    inv.accepted_user_id = user.id
    audit(db, user.id, "invitation.accept" if inv.kind == "access" else "password.reset", "invitation", inv.id, role=user.role)
    return user
