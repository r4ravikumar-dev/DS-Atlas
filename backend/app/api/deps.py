"""Request dependencies: DB session, current user, permission checks, CSRF, pagination."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from ..core.exceptions import AppError, Forbidden, Unauthorized
from ..core.permissions import PUBLIC, has_permission
from ..core.security import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, decode_session_token
from ..database.session import get_db
from ..models import User

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass
class Principal:
    user: User | None
    via_cookie: bool

    @property
    def role(self) -> str | None:
        return self.user.role if self.user else None

    @property
    def id(self) -> uuid.UUID | None:
        return self.user.id if self.user else None


def get_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    token, via_cookie = None, False
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    elif request.cookies.get(SESSION_COOKIE):
        token, via_cookie = request.cookies[SESSION_COOKIE], True
    if not token:
        return Principal(None, False)
    data = decode_session_token(token)
    if not data:
        return Principal(None, False)
    try:
        user = db.get(User, uuid.UUID(data["sub"]))
    except (ValueError, KeyError):
        user = None
    if not user or not user.is_active or data.get("sv") != user.session_version:
        return Principal(None, False)  # unknown, deactivated, or revoked session (role changes also bump the version)
    # CSRF: cookie-authenticated unsafe requests must echo the CSRF cookie in a header
    if via_cookie and request.method not in SAFE_METHODS:
        c, h = request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)
        if not c or not h or c != h:
            raise AppError("Missing or invalid CSRF token.", code="CSRF_FAILED", status_code=403)
    return Principal(user, via_cookie)


def require(permission: str):
    def dep(request: Request, p: Principal = Depends(get_principal)) -> Principal:
        if permission in PUBLIC:
            # published data: no account needed (rate-limited per client in the HTTP middleware). Anyone but an
            # administrator gets the public presentation model (see api/public_projection.py).
            request.state.public_view = p.role != "admin"
            return p
        if p.user is None:
            raise Unauthorized("Authentication required.")
        if not has_permission(p.role, permission):
            raise Forbidden("Administrator access required.")
        return p
    return dep


@dataclass
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(page: int = Query(1, ge=1, le=10000), page_size: int = Query(25, ge=1, le=100)) -> PageParams:
    return PageParams(page, page_size)
