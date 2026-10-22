"""Single-administrator model: every protected capability requires an active administrator session.
The capability names document what each endpoint does; they all resolve to the admin role and are enforced in the backend."""
from __future__ import annotations

PERMISSIONS = frozenset({
    "read", "search", "source:create", "source:update", "crawl:start", "job:cancel", "job:retry", "comparison:write",
    "export:create", "review:resolve", "system:write", "admin:config", "admin:audit",
})


def has_permission(role: str | None, permission: str) -> bool:
    if permission not in PERMISSIONS:
        raise KeyError(permission)
    return role == "admin"
