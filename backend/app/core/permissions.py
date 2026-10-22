"""Public directory + single administrator.

* `public:read` — the published research data (systems, components, tokens, guidelines, Storybook, search, compare).
  Anyone may read it, without an account.
* Every other capability (sources, crawls, jobs, raw documents, review, quality, exports, settings, sync) requires an active
  administrator session and is enforced in the backend on every request."""
from __future__ import annotations

PUBLIC = frozenset({"public:read"})
PERMISSIONS = frozenset({"public:read",
    "read", "search", "source:create", "source:update", "crawl:start", "job:cancel", "job:retry", "comparison:write",
    "export:create", "review:resolve", "system:write", "admin:config", "admin:audit",
})


def has_permission(role: str | None, permission: str) -> bool:
    if permission not in PERMISSIONS:
        raise KeyError(permission)
    return permission in PUBLIC or role == "admin"
