"""Typed resource links of canonical design systems (official website, documentation, GitHub, Figma, Storybook, other).

`sync(db)` runs inside every build. It derives candidate links from the canonical rows and the source records that
resolved to them, keeps provenance (which sources listed each link), remaps links of merged systems to the surviving
system, and marks a link *verified* only from evidence:
  * official-docs crawl evidence (`attribute_evidence` identity.official_docs / identity.repository),
  * resolver decisions that verified the official docs URL over HTTP (`entity_curation` with evidence),
  * the verifier job below (the system's official page links to the resource),
  * an administrator confirming it.
Statuses set by the verifier or an administrator are never downgraded by a rebuild. URLs are never constructed or guessed.

`verify(db, ...)` fetches each system's official page (robots/SSRF/allow-list/rate limits via the engine fetcher) and
confirms or discovers repository, Figma and Storybook links published on it."""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import AttributeEvidence, DesignSystem, EntityCuration, Record, Source, StorybookProject, SystemAlias, SystemResource
from ..scrapers.dskb import core as engine

log = logging.getLogger("app.resources")
TYPE_ORDER = ["official_website", "official_documentation", "github_repository", "figma_file", "storybook", "additional_resource"]
ORIGIN_RANK = {"manual": 5, "official_site": 4, "official_docs": 4, "resolver": 3, "storybook_showcase": 2, "directory": 1}
SOCIAL = re.compile(r"(^|\.)(linkedin\.com|twitter\.com|x\.com|facebook\.com|instagram\.com|youtube\.com|medium\.com|dribbble\.com|discord\.(gg|com)|"
                    r"npmjs\.com|stackoverflow\.com|reddit\.com|t\.me|mastodon\.social|bsky\.app)$")
# Design files only: profile pages (figma.com/@org), plugins and the generic community landing page are not design files.
FIGMA_FILE = re.compile(r"^https?://(www\.)?figma\.com/(file|design|proto|board|slides|community/file)/[\w-]+", re.I)
# Hosts whose pages are not a design system's own site (a repository page links to the host's own product pages).
CODE_HOSTS = re.compile(r"(^|\.)(github\.com|gitlab\.com|bitbucket\.org|npmjs\.com|medium\.com|codesandbox\.io|stackblitz\.com)$")
GITHUB_RESERVED = {"orgs", "topics", "sponsors", "features", "about", "marketplace", "collections", "security", "pricing", "enterprise", "team",
                   "customer-stories", "readme", "settings", "login", "join", "site", "contact", "git-guides", "github", "apps", "explore",
                   "trending", "events", "resources", "solutions", "open-source", "readme", "about", "home", "skills", "partners", "premium-support", "newsroom", "mobile", "codespaces", "copilot", "pulls",
                   "issues", "notifications", "new", "organizations", "account", "dashboard", "search", "en", "docs"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def host(u: str | None) -> str:
    return (urlparse(u or "").hostname or "").lower().removeprefix("www.")


def github_repo(u: str | None) -> str | None:
    """https://github.com/owner/repo (lowercase) for repository-like GitHub/GitLab URLs, else None."""
    if not u:
        return None
    m = re.match(r"https?://(www\.)?(github\.com|gitlab\.com)/([\w.-]+)/([\w.-]+)", u.strip(), re.I)
    if not m or m.group(3).lower() in GITHUB_RESERVED:
        return None
    return f"https://{m.group(2).lower()}/{m.group(3).lower()}/{m.group(4).lower().removesuffix('.git')}"


def github_owner(u: str | None) -> str | None:
    m = re.match(r"https?://(www\.)?(github\.com|gitlab\.com)/([\w.-]+)/?", (u or "").strip(), re.I)
    return f"{m.group(2).lower()}/{m.group(3).lower()}" if m and m.group(3).lower() not in GITHUB_RESERVED else None


_NAME_STOP = {"design", "system", "systems", "ds", "ui", "the", "kit", "library", "components", "component", "docs", "www", "com", "io", "org", "net",
              "app", "dev", "co", "uk", "gov", "github", "gitlab", "style", "guide", "styleguide", "web", "framework", "vercel", "netlify", "pages", "react"}


def _tokens(*texts: str | None) -> set[str]:
    out: set[str] = set()
    for t in texts:
        for w in re.findall(r"[a-z0-9]+", (t or "").lower()):
            if len(w) >= 3 and w not in _NAME_STOP:
                out.add(w)
        joined = re.sub(r"[^a-z0-9]", "", (t or "").lower())
        if len(joined) >= 4:
            out.add(joined)
    return out


def repo_owned_by_system(repo_url: str, system_name: str | None, organization: str | None, site_url: str | None, known_owners: set[str]) -> bool:
    """Ownership evidence for a repository linked from an official page: its owner is already associated with the system, or the
    owner/repository name matches the system's name, organization or site host. Dependency credits and community lists do not match."""
    owner = github_owner(repo_url)
    if not owner:
        return False
    if owner in known_owners:
        return True
    repo_name = repo_url.rstrip("/").rsplit("/", 1)[-1].lower()
    sys_tokens = _tokens(system_name, organization, *host(site_url).split("."), host(site_url).replace(".", ""))
    if sys_tokens & _tokens(owner.split("/", 1)[1]):
        return True  # the owning account is named after the system, its organization or its site
    if "awesome" in repo_name:
        return False  # curated community lists link everything
    return any(len(t) >= 4 for t in sys_tokens & _tokens(repo_name))


def repo_name_matches(repo_url: str, system_name: str | None, aliases: list[str] | None = None, organization: str | None = None) -> bool:
    """The repository's own name carries a distinctive token of the system's name (e.g. Shopify/polaris for Polaris).
    Organization words are excluded, so shopify/remote-dom or shopify/shopify-cli do not match "Shopify Polaris"."""
    repo_name = repo_url.rstrip("/").rsplit("/", 1)[-1]
    name_tokens = _tokens(system_name, *(aliases or []))
    org_tokens = _tokens(organization) - _tokens(system_name)  # keep them when the system is named after its company
    return any(len(t) >= 4 for t in _tokens(repo_name) & (name_tokens - org_tokens))


def classify(url: str) -> str:
    h = host(url)
    if github_repo(url):
        return "github_repository"
    if h.endswith("figma.com"):
        return "figma_file" if FIGMA_FILE.match(url) else "additional_resource"
    if "storybook" in h or h.endswith("chromatic.com") or "/storybook" in urlparse(url).path.lower():
        return "storybook"
    return "additional_resource"


def canon(rtype: str, url: str) -> str:
    if rtype == "github_repository":
        return github_repo(url) or engine.canonical_url(url) or url
    if rtype == "figma_file":  # node-id / viewport / mode query parameters point inside the same file
        p = urlparse(url)
        return f"https://www.figma.com{p.path.rstrip('/')}"
    c = engine.canonical_url(url) or url
    return re.sub(r"^http://", "https://", c)


class _Cands:
    def __init__(self) -> None:
        self.by: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add(self, key: str, rtype: str, url: str | None, origin: str, source: str | None = None, *, status: str = "unverified",
            method: str | None = None, evidence_url: str | None = None, note: str | None = None, label: str | None = None) -> None:
        if not url or not url.startswith("http") or len(url) > 2000:
            return
        if rtype == "figma_file" and not FIGMA_FILE.match(url):
            rtype = "additional_resource"  # a generic figma.com page is not a design file
        c = canon(rtype, url)
        k = (key, rtype, c)
        cur = self.by.get(k)
        if not cur:
            cur = self.by[k] = {"system_key": key, "resource_type": rtype, "url": url, "canonical_url": c, "origin": origin, "source_keys": set(),
                                "verification_status": "unverified", "verification_method": None, "evidence_url": None, "evidence_note": None, "label": label}
        if source:
            cur["source_keys"].add(source)
        if ORIGIN_RANK.get(origin, 0) > ORIGIN_RANK.get(cur["origin"], 0):
            cur["origin"] = origin
        if status == "verified" and cur["verification_status"] != "verified":
            cur.update(verification_status="verified", verification_method=method, evidence_url=evidence_url, evidence_note=note)
        elif note and not cur.get("evidence_note"):
            cur["evidence_note"] = note


def _derive(db: Session) -> _Cands:
    cands = _Cands()
    systems = db.execute(select(DesignSystem.id, DesignSystem.key, DesignSystem.documentation_url, DesignSystem.official_docs_url, DesignSystem.repository_url,
                                DesignSystem.storybook_url, DesignSystem.design_resource_url, DesignSystem.related_urls)).all()
    keys = {sid: key for sid, key, *_ in systems}
    curated = {(c.entity_key, c.field): c for c in db.scalars(select(EntityCuration).where(EntityCuration.field.in_(["official_docs_url", "repository_url"])))}
    aliases = dict(db.execute(select(SystemAlias.alias_key, SystemAlias.canonical_key)).all())

    def resolve(k: str) -> str:
        seen = set()
        while k in aliases and k not in seen:
            seen.add(k)
            k = aliases[k]
        return k

    for sid, key, docs, off_docs, repo, sb, design, related in systems:
        cur = curated.get((key, "official_docs_url"))
        if off_docs:
            verified = bool(cur and cur.value == off_docs and cur.evidence)
            cands.add(key, "official_documentation", off_docs, "resolver" if verified else "directory",
                      status="verified" if verified else "unverified", method="resolver_http" if verified else None,
                      evidence_url=((cur.evidence or [{}])[0].get("url") if verified and isinstance((cur.evidence or [{}])[0], dict) else None),
                      note="Official documentation URL confirmed over HTTP during identity review." if verified else None)
        if docs and docs != off_docs:
            path = urlparse(docs).path.strip("/")
            cands.add(key, "official_website" if not path else "official_documentation", docs, "directory")
        if repo:
            cands.add(key, "github_repository" if github_repo(repo) else "additional_resource", repo, "directory")
        if sb:
            cands.add(key, "storybook", sb, "directory")
        if design:
            cands.add(key, "figma_file" if host(design).endswith("figma.com") else "additional_resource", design, "directory")
        for u in related or []:
            cands.add(key, classify(u), u, "directory")

    # provenance: which sources listed each link (system/tool records resolved to the canonical system)
    src_keys = dict(db.execute(select(Source.id, Source.key)).all())
    src_origin = dict(db.execute(select(Source.key, Source.origin)).all())
    rows = db.execute(select(Record.system_id, Record.source_id, Record.content)
                      .where(Record.system_id.is_not(None), Record.record_type.in_(["system", "tool"]), Record.is_stale.is_(False))).all()
    for sid, source_id, content in rows:
        key, sk = keys.get(sid), src_keys.get(source_id)
        if not key or not isinstance(content, dict):
            continue
        origin = "official_docs" if src_origin.get(sk) == "official" else "directory"
        for field, rtype in (("documentation_url", None), ("repository_url", "github_repository"), ("storybook_url", "storybook"), ("design_resource_url", "figma_file")):
            u = content.get(field)
            if not u:
                continue
            t = rtype or ("official_website" if not urlparse(u).path.strip("/") else "official_documentation")
            if t == "github_repository" and not github_repo(u):
                t = "additional_resource"
            ok = origin == "official_docs" and t in ("official_website", "official_documentation")
            cands.add(key, t, u, origin, sk, status="verified" if ok else "unverified", method="official_docs_crawl" if ok else None,
                      evidence_url=u if ok else None, note="Crawled as the system's official documentation." if ok else None)

    names = {key: (name, aliases or [], org) for key, name, aliases, org in db.execute(
        select(DesignSystem.key, DesignSystem.name, DesignSystem.aliases, DesignSystem.organization))}
    # official-docs crawl evidence
    for skey, path, value, url, vstatus in db.execute(select(AttributeEvidence.system_key, AttributeEvidence.attribute_path, AttributeEvidence.value,
                                                             AttributeEvidence.source_url, AttributeEvidence.verification_status)
                                                      .where(AttributeEvidence.attribute_path.in_(["identity.official_docs", "identity.repository"]))):
        key = resolve(skey)
        v = value if isinstance(value, str) else (value or {}).get("url") if isinstance(value, dict) else None
        if not v or vstatus != "verified":
            continue
        t = "github_repository" if path == "identity.repository" else ("official_website" if not urlparse(v).path.strip("/") else "official_documentation")
        if t == "github_repository" and not repo_name_matches(v, *names.get(key, (None, [], None))):
            # an organization's docs link many of its repositories; only one named after the system is evidence of *its* repository
            cands.add(key, t, v, "official_docs", note="Linked from the official documentation; the repository name does not match the system.")
            continue
        cands.add(key, t, v, "official_docs", status="verified", method="official_docs_crawl", evidence_url=url,
                  note=f"Recorded as {path} by the official documentation crawl.")

    # Storybook projects reached through the Storybook showcase (public index fetched = reachable deployment)
    for skey, url, resolved, status in db.execute(select(StorybookProject.system_key, StorybookProject.storybook_url, StorybookProject.resolved_url,
                                                         StorybookProject.status).where(StorybookProject.system_key.is_not(None))):
        cands.add(resolve(skey), "storybook", resolved or url, "storybook_showcase", "S04", label="Storybook showcase project")
    return cands


def sync(db: Session) -> dict[str, int]:
    """Idempotent: re-derives non-manual links, preserves verifier/admin decisions, remaps merged systems, resolves system ids."""
    t = now()
    # 1. move links of merged (aliased) systems to their canonical system
    db.execute(text("""
        WITH RECURSIVE chain(alias_key, canonical_key, depth) AS (
            SELECT alias_key, canonical_key, 1 FROM system_aliases
            UNION ALL SELECT c.alias_key, a.canonical_key, c.depth + 1 FROM chain c JOIN system_aliases a ON a.alias_key = c.canonical_key WHERE c.depth < 10)
        , final AS (SELECT DISTINCT ON (alias_key) alias_key, canonical_key FROM chain ORDER BY alias_key, depth DESC)
        DELETE FROM system_resources r USING final f, system_resources keep
        WHERE r.system_key = f.alias_key AND keep.system_key = f.canonical_key AND keep.resource_type = r.resource_type AND keep.canonical_url = r.canonical_url
          AND (keep.verification_status = 'verified' OR r.verification_status <> 'verified')"""))
    db.execute(text("""
        WITH RECURSIVE chain(alias_key, canonical_key, depth) AS (
            SELECT alias_key, canonical_key, 1 FROM system_aliases
            UNION ALL SELECT c.alias_key, a.canonical_key, c.depth + 1 FROM chain c JOIN system_aliases a ON a.alias_key = c.canonical_key WHERE c.depth < 10)
        , final AS (SELECT DISTINCT ON (alias_key) alias_key, canonical_key FROM chain ORDER BY alias_key, depth DESC)
        DELETE FROM system_resources keep USING final f, system_resources r
        WHERE r.system_key = f.alias_key AND keep.system_key = f.canonical_key AND keep.resource_type = r.resource_type AND keep.canonical_url = r.canonical_url"""))
    db.execute(text("""
        WITH RECURSIVE chain(alias_key, canonical_key, depth) AS (
            SELECT alias_key, canonical_key, 1 FROM system_aliases
            UNION ALL SELECT c.alias_key, a.canonical_key, c.depth + 1 FROM chain c JOIN system_aliases a ON a.alias_key = c.canonical_key WHERE c.depth < 10)
        , final AS (SELECT DISTINCT ON (alias_key) alias_key, canonical_key FROM chain ORDER BY alias_key, depth DESC)
        UPDATE system_resources r SET system_key = f.canonical_key, updated_at = now() FROM final f WHERE r.system_key = f.alias_key"""))

    # 1b. canonical form changes (e.g. Figma node-id query stripped): re-key existing rows, keeping the best of any duplicates
    _recanonicalize(db)

    # 2. derive and upsert
    cands = _derive(db)
    existing = {(r.system_key, r.resource_type, r.canonical_url): r for r in db.scalars(select(SystemResource))}
    added = updated = removed = 0
    for k, c in cands.by.items():
        r = existing.get(k)
        srcs = sorted(c["source_keys"])
        if r is None:
            db.add(SystemResource(**{**c, "source_keys": srcs}))
            added += 1
            continue
        r.source_keys = sorted(set(r.source_keys or []) | set(srcs)) if r.origin == "manual" else srcs
        if r.origin != "manual" and ORIGIN_RANK.get(c["origin"], 0) >= ORIGIN_RANK.get(r.origin, 0):
            r.origin = c["origin"]
        decided = r.verification_method and (r.verification_method.startswith("verifier") or r.verification_method == "admin")
        if c["verification_status"] == "verified" and r.verification_status != "verified" and not (decided and r.verification_status == "invalid"):
            r.verification_status, r.verification_method = "verified", c["verification_method"]
            r.evidence_url, r.evidence_note = c["evidence_url"], c["evidence_note"]
        elif not decided and r.verification_status == "verified" and c["verification_status"] != "verified" and r.verification_method in (
                "official_docs_crawl", "resolver_http"):
            # the derivation rule no longer treats this as evidence (e.g. repository named after another product)
            r.verification_status, r.verification_method, r.evidence_note = "unverified", None, c.get("evidence_note")
        updated += 1
    # links no longer listed by any source disappear, unless an administrator added them or the verifier discovered them
    for k, r in existing.items():
        if k not in cands.by and r.origin not in ("manual", "official_site"):
            db.delete(r)
            removed += 1
    db.flush()
    # 3. resolve system ids; orphaned links (system vanished without an alias) keep their key but no id
    db.execute(text("UPDATE system_resources r SET system_id = d.id FROM design_systems d WHERE d.key = r.system_key AND r.system_id IS DISTINCT FROM d.id"))
    db.execute(text("UPDATE system_resources r SET system_id = NULL WHERE NOT EXISTS (SELECT 1 FROM design_systems d WHERE d.key = r.system_key)"))
    _choose_primary(db)
    log.info("resources synced", extra={"added": added, "updated": updated, "removed": removed, "duration_ms": int((now() - t).total_seconds() * 1000)})
    return {"added": added, "updated": updated, "removed": removed}


def _recanonicalize(db: Session) -> None:
    rows = db.scalars(select(SystemResource).where(SystemResource.resource_type.in_(["figma_file", "github_repository"]))).all()
    groups: dict[tuple[str, str, str], list[SystemResource]] = defaultdict(list)
    for r in rows:
        groups[(r.system_key, r.resource_type, canon(r.resource_type, r.url))].append(r)
    for (_, _, c), rs in groups.items():
        if len(rs) == 1 and rs[0].canonical_url == c:
            continue
        rs.sort(key=lambda r: (r.verification_status != "verified", -ORIGIN_RANK.get(r.origin, 0), r.id))
        keep, extra = rs[0], rs[1:]
        keep.source_keys = sorted({k for r in rs for k in (r.source_keys or [])})
        for r in extra:
            db.delete(r)
        db.flush()
        keep.canonical_url = c
    db.flush()


def _choose_primary(db: Session) -> None:
    """One primary link per (system, type): verified first; for repositories, one named after the system; then origin and corroboration."""
    names = {key: (name, aliases or [], org) for key, name, aliases, org in db.execute(
        select(DesignSystem.key, DesignSystem.name, DesignSystem.aliases, DesignSystem.organization))}
    groups: dict[tuple[str, str], list[SystemResource]] = defaultdict(list)
    for r in db.scalars(select(SystemResource)):
        groups[(r.system_key, r.resource_type)].append(r)
    for (key, rtype), rs in groups.items():
        live = [r for r in rs if r.verification_status != "invalid"]
        best = min(live, key=lambda r: (r.verification_status != "verified",
                                        not (rtype == "github_repository" and repo_name_matches(r.canonical_url, *names.get(key, (None, [], None))))
                                        if rtype == "github_repository" else False,
                                        -ORIGIN_RANK.get(r.origin, 0), -len(r.source_keys or []), r.id)) if live else None
        for r in rs:
            want = r is best
            if r.is_primary != want:
                r.is_primary = want
    db.flush()


# ───────────────────────────── verifier ─────────────────────────────

def _page_links(r) -> list[str]:
    from bs4 import BeautifulSoup
    out: list[str] = []
    try:
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:  # noqa: BLE001
        return out
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith(("mailto:", "javascript:", "#", "tel:")):
            continue
        u = urljoin(r.final_url, h)
        if u.startswith("http") and u not in out:
            out.append(u)
    return out[:2000]


def verify(db: Session, *, system_ids: list[int] | None = None, system_keys: list[str] | None = None,
           progress: Callable[[int, int, str], None] | None = None, workers: int = 8) -> dict[str, Any]:
    """Fetch each system's primary official page; mark it reachable/invalid; verify or discover repository, Figma and Storybook
    links it publishes. Idempotent (upserts by system/type/canonical URL)."""
    from .evidence_fetch import approve_hosts
    q = select(SystemResource).where(SystemResource.resource_type.in_(["official_documentation", "official_website"]),
                                     SystemResource.is_primary.is_(True), SystemResource.system_id.is_not(None))
    if system_ids:
        q = q.where(SystemResource.system_id.in_(system_ids))
    if system_keys:
        q = q.where(SystemResource.system_key.in_(system_keys))
    pages = db.scalars(q).all()
    by_sys: dict[str, list[SystemResource]] = defaultdict(list)
    for p in pages:
        by_sys[p.system_key].append(p)
    targets = []
    for k, v in by_sys.items():
        own = [r for r in v if not CODE_HOSTS.search(host(r.url))]  # a repository page is not the system's own site
        if own:
            targets.append((k, sorted(own, key=lambda r: TYPE_ORDER.index(r.resource_type))[0]))
    approve_hosts([p.url for _, p in targets])

    def fetch(item):
        k, res = item
        url = re.sub(r"^http://", "https://", res.url)
        r = engine.FETCHER.get(url, source_id="VERIFY", timeout=15, retries=1)
        if r is None and url != res.url:
            r = engine.FETCHER.get(res.url, source_id="VERIFY", timeout=15, retries=1)
        return k, res.id, r

    summary = {"systems_checked": 0, "pages_ok": 0, "pages_invalid": 0, "pages_unreachable": 0, "repos_verified": 0, "repos_discovered": 0,
               "figma_found": 0, "storybooks_found": 0, "limitations": []}
    t = now()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(fetch, targets))
    for i, (key, res_id, r) in enumerate(results, 1):
        summary["systems_checked"] += 1
        if progress and (i % 10 == 0 or i == len(results)):
            progress(i, len(results), key)
        try:
            with db.begin_nested():  # one system's failure must not discard the others
                _check_one(db, key, res_id, r, t, summary)
        except Exception as e:  # noqa: BLE001
            summary.setdefault("errors", []).append(f"{key}: {type(e).__name__}")
            log.warning("resource verification failed for one system", extra={"system": key, "error": type(e).__name__})
    _choose_primary(db)
    summary["limitations"].append("Only static HTML links are read; links rendered exclusively by client-side JavaScript are not seen, "
                                  "so 'not found' means not published in the page's HTML, not proof of absence.")
    return summary


def _check_one(db: Session, key: str, res_id: int, r, t: datetime, summary: dict[str, Any]) -> None:
    res = db.get(SystemResource, res_id)
    res.last_checked_at = t
    if r is None:
        summary["pages_unreachable"] += 1
        res.access_note = "Not fetched (robots.txt, allow-list, network or timeout); reachability unknown."
        return
    res.http_status = r.status
    if r.status in (404, 410) or r.status >= 500:
        res.verification_status, res.verification_method = "invalid", "verifier_http"
        res.evidence_note = f"HTTP {r.status} when checked."
        summary["pages_invalid"] += 1
        return
    if not (200 <= r.status < 400):
        res.access_note = f"HTTP {r.status} (access restricted or bot protection); not treated as broken."
        return
    summary["pages_ok"] += 1
    if r.final_url and host(r.final_url) != host(res.url):
        res.access_note = f"Redirects to {r.final_url}"
    links = _page_links(r)
    ev = r.final_url or res.url
    owners = {github_owner(u) for u in links if github_owner(u)}
    repos = {github_repo(u) for u in links if github_repo(u)}
    sysrow = db.get(DesignSystem, res.system_id) if res.system_id else None
    known_owners = {github_owner(c) for c in db.scalars(select(SystemResource.canonical_url).where(
        SystemResource.system_key == key, SystemResource.resource_type == "github_repository", SystemResource.origin != "official_site")) if github_owner(c)}
    # existing repository candidates of this system
    for cand in db.scalars(select(SystemResource).where(SystemResource.system_key == key, SystemResource.resource_type == "github_repository")):
        cand.last_checked_at = t
        if cand.canonical_url in repos and (cand.origin != "official_site" or repo_owned_by_system(
                cand.canonical_url, sysrow and sysrow.name, sysrow and sysrow.organization, res.url, known_owners)):
            _mark(cand, "verifier_official_page_link", ev, "Linked from the system's official page.")
            summary["repos_verified"] += 1
        elif github_owner(cand.canonical_url) in owners and cand.verification_status != "verified":
            _mark(cand, "verifier_official_page_links_owner", ev, f"The official page links the {github_owner(cand.canonical_url)} organization that owns this repository.")
            summary["repos_verified"] += 1
    seen: set[tuple[str, str]] = set()
    for u in links:
        h = host(u)
        if SOCIAL.search(h):
            continue
        rtype = None
        if github_repo(u) and not re.search(r"/(issues|pulls|discussions|releases|blob|tree|wiki|actions|compare|commit)(/|$)", urlparse(u).path):
            rtype = "github_repository"
        elif h.endswith("figma.com") and FIGMA_FILE.match(u):
            rtype = "figma_file"
        elif ("storybook" in h or h.endswith("chromatic.com")) and h != host(res.url):
            rtype = "storybook"
        if not rtype or (rtype, canon(rtype, u)) in seen:
            continue
        seen.add((rtype, canon(rtype, u)))
        note = {"github_repository": "Repository linked from the system's official page.",
                "figma_file": "Figma resource linked from the system's official page.",
                "storybook": "Storybook linked from the system's official page."}[rtype]
        owned = rtype != "github_repository" or repo_owned_by_system(u, sysrow and sysrow.name, sysrow and sysrow.organization, res.url, known_owners)
        if not owned:
            note = "Linked from the system's official page, but ownership is not established (may be a dependency, credit or community project)."
        created = _upsert(db, key, res.system_id, rtype, u, ev, note, t, verified=owned,
                          access="Figma community/file links may require a Figma account to open." if rtype == "figma_file" else None)
        if rtype == "github_repository" and created:
            summary["repos_discovered"] += 1
        elif rtype == "figma_file":
            summary["figma_found"] += 1
        elif rtype == "storybook":
            summary["storybooks_found"] += 1
    db.flush()


def _mark(r: SystemResource, method: str, evidence_url: str, note: str) -> None:
    r.verification_status, r.verification_method, r.evidence_url, r.evidence_note = "verified", method, evidence_url, note


def _upsert(db: Session, key: str, system_id: int | None, rtype: str, url: str, ev: str, note: str, t: datetime, access: str | None = None,
            verified: bool = True) -> bool:
    c = canon(rtype, url)
    r = db.scalar(select(SystemResource).where(SystemResource.system_key == key, SystemResource.resource_type == rtype, SystemResource.canonical_url == c))
    if r is None:
        db.add(SystemResource(system_key=key, system_id=system_id, resource_type=rtype, url=c if rtype in ("github_repository", "figma_file") else url,
                              canonical_url=c, origin="official_site", source_keys=[], verification_status="verified" if verified else "unverified",
                              verification_method="verifier_official_page_link" if verified else "verifier_linked_not_owned",
                              evidence_url=ev, evidence_note=note, access_note=access, last_checked_at=t))
        db.flush()
        return True
    r.last_checked_at = t
    if verified and r.verification_status != "verified":
        _mark(r, "verifier_official_page_link", ev, note)
    elif not verified and r.origin == "official_site" and r.verification_method == "verifier_official_page_link":
        # re-evaluated under the ownership rule: a link alone is not ownership
        r.verification_status, r.verification_method, r.evidence_note = "unverified", "verifier_linked_not_owned", note
    if access and not r.access_note:
        r.access_note = access
    return False
