"""Authentication primitives (standard building blocks only):
* Argon2id password hashing (pwdlib).
* Signed, expiring session tokens (JWT HS256) delivered in an httpOnly, SameSite=Lax cookie,
  or as a Bearer token for API clients.
* CSRF protection via double-submit cookie for cookie-authenticated unsafe requests."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from .config import get_settings

SESSION_COOKIE = "dsrp_session"
CSRF_COOKIE = "dsrp_csrf"
CSRF_HEADER = "x-csrf-token"
_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(password, hashed)
    except Exception:
        return False


def create_session_token(user_id: str, role: str, session_version: int = 1) -> str:
    """`sv` must equal users.session_version at request time; bumping the column revokes every outstanding session."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {"sub": user_id, "role": role, "sv": session_version, "iat": now,
                               "exp": now + timedelta(minutes=s.session_ttl_minutes), "typ": "session"}
    return jwt.encode(payload, s.secret_key, algorithm="HS256")


def decode_session_token(token: str) -> dict[str, Any] | None:
    try:
        data = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        return data if data.get("typ") == "session" else None
    except jwt.PyJWTError:
        return None


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def create_download_token(job_id: str, user_id: str, ttl_minutes: int = 10) -> str:
    """Short-lived signed token allowing a single export download URL to be opened."""
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "job": job_id, "typ": "download", "exp": now + timedelta(minutes=ttl_minutes)}, get_settings().secret_key, algorithm="HS256")


def decode_download_token(token: str) -> dict[str, Any] | None:
    try:
        d = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        return d if d.get("typ") == "download" else None
    except jwt.PyJWTError:
        return None
