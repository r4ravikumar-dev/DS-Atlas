"""Role-based permissions, enforced in the backend regardless of frontend visibility."""
from __future__ import annotations

ROLE_RANK = {"viewer": 1, "researcher": 2, "admin": 3}

PERMISSIONS: dict[str, str] = {
    "read": "viewer",
    "search": "viewer",
    "source:create": "researcher",
    "source:update": "researcher",
    "crawl:start": "researcher",
    "job:cancel": "researcher",
    "job:retry": "researcher",
    "comparison:write": "researcher",
    "export:create": "researcher",
    "review:resolve": "researcher",
    "system:write": "researcher",
    "admin:users": "admin",
    "admin:config": "admin",
    "admin:audit": "admin",
}


def has_permission(role: str | None, permission: str) -> bool:
    need = PERMISSIONS[permission]
    return ROLE_RANK.get(role or "", 0) >= ROLE_RANK[need]
