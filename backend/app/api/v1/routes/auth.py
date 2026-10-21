from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....core.config import get_settings
from ....core.exceptions import AppError, Unauthorized
from ....core.security import CSRF_COOKIE, SESSION_COOKIE, create_session_token, new_csrf_token, verify_password
from ....database.session import get_db
from ....models import User
from ....schemas import Item, LoginRequest, SessionOut, UserOut
from ....services.audit import audit
from ...deps import Principal, get_principal
from ..common import ERRORS

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERRORS)
_FAILS: dict[str, list[float]] = {}


def _rate_limit(key: str) -> None:
    import time
    now = time.time()
    hits = [t for t in _FAILS.get(key, []) if now - t < 300]
    _FAILS[key] = hits
    if len(hits) >= 10:
        raise AppError("Too many failed sign-in attempts. Try again in a few minutes.", code="RATE_LIMITED", status_code=429)


@router.post("/login", response_model=Item[SessionOut], summary="Sign in (sets httpOnly session + CSRF cookies)")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    import time
    key = body.email.lower()
    _rate_limit(key)
    user = db.scalar(select(User).where(func.lower(User.email) == key))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        _FAILS.setdefault(key, []).append(time.time())
        raise Unauthorized("Invalid email or password.")
    s = get_settings()
    token = create_session_token(str(user.id), user.role)
    csrf = new_csrf_token()
    max_age = s.session_ttl_minutes * 60
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=s.cookie_secure, samesite="lax", max_age=max_age, path="/", domain=s.cookie_domain)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=s.cookie_secure, samesite="lax", max_age=max_age, path="/", domain=s.cookie_domain)
    user.last_login_at = datetime.now(timezone.utc)
    audit(db, user.id, "auth.login", "user", user.id)
    db.commit()
    return {"data": {"user": user, "csrf_token": csrf, "expires_in_seconds": max_age}}


@router.post("/logout", status_code=204, summary="Sign out")
def logout(response: Response, p: Principal = Depends(get_principal)):
    s = get_settings()
    response.delete_cookie(SESSION_COOKIE, path="/", domain=s.cookie_domain)
    response.delete_cookie(CSRF_COOKIE, path="/", domain=s.cookie_domain)
    response.status_code = 204
    return response


@router.get("/me", response_model=Item[UserOut], summary="Current user")
def me(p: Principal = Depends(get_principal)):
    if p.user is None:
        raise Unauthorized("Not signed in.")
    return {"data": p.user}
