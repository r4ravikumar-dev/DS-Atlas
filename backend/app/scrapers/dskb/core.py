"""Core infrastructure: configuration, polite HTTP fetching with robots/caching/retries,
GitHub access, provenance logging, record construction and Markdown parsing helpers."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.robotparser
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

warnings.filterwarnings("ignore")  # LibreSSL notice from urllib3 on macOS system Python
import requests  # noqa: E402

SCHEMA_VERSION = "1.0.0"
ROOT = Path(os.environ.get("DSKB_DATA_DIR") or Path(__file__).resolve().parents[3] / "storage" / "engine")
DATA = ROOT / "data"
CACHE = DATA / "cache"
STAGE = DATA / "stage"
OUT = ROOT / "output"


class JobCancelled(Exception):
    """Raised by a fetch listener to abort a running adapter cooperatively."""


class UnsafeDestination(Exception):
    pass


def is_public_host(host: str) -> bool:
    """SSRF guard: every resolved address must be globally routable (no private, loopback,
    link-local, reserved, multicast or cloud-metadata ranges)."""
    import ipaddress
    import socket
    host = host.split(":")[0].strip("[]")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
                or ip.is_unspecified or str(ip) in ("169.254.169.254", "fd00:ec2::254")):
            return False
    return True


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ───────────────────────────── configuration ─────────────────────────────
@dataclass
class CrawlConfig:
    user_agent: str = "DSKB-Research/1.0 (design-system knowledge-base research; polite crawler)"
    max_depth: int = 3
    per_host_delay: float = 1.0  # seconds between requests to one host (raised by robots crawl-delay)
    timeout: float = 30.0
    retries: int = 3
    backoff_base: float = 2.0
    max_bytes: int = 12 * 1024 * 1024
    cache_ttl_hours: float = 24 * 7
    refresh: bool = False
    max_pages_per_source: int = 600
    # Domains we may request. Seeds + their official docs/API/raw-repo hosts.
    allow_domains: Tuple[str, ...] = (
        "designsystems.surf", "adele.uxpin.com", "designsystemsrepo.com", "storybook.js.org",
        "designsystems.directory", "github.com", "api.github.com", "raw.githubusercontent.com",
        "ui.shadcn.com", "www.radix-ui.com", "base-ui.com", "react-spectrum.adobe.com",
        "react-aria.adobe.com", "mantine.dev", "ant.design", "thedesignsystem.guide",
        "www.designsystems.com", "designsystems.com", "www.designsystems.one", "registry.npmjs.org",
        "styledictionary.com", "www.designtokens.org", "tr.designtokens.org", "designtokens.org",
        "www.designsystemchecklist.com", "cdn.jsdelivr.net",
    )
    deny_patterns: Tuple[str, ...] = (r"/my-signin", r"/login", r"/signup", r"utm_", r"/cart", r"/checkout")


CONFIG = CrawlConfig()


# ───────────────────────────── URL helpers ─────────────────────────────
TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "gclid", "fbclid"}


def canonical_url(url: Optional[str]) -> Optional[str]:
    """Normalise scheme/host case, drop fragments and tracking params, trim trailing slash (not root)."""
    if not url:
        return url
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    p = urlparse(url)
    if not p.scheme:
        return url
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING and not k.lower().startswith("utm_")]
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(q), ""))


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower()


def slugify(s: str, maxlen: int = 80) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s.-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_.]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:maxlen] or "x"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ───────────────────────────── provenance log ─────────────────────────────
class Manifest:
    """Append-only crawl manifest (durable frontier/outcome log) shared by all fetchers."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: Dict[str, Any]) -> None:
        entry.setdefault("logged_at", now_iso())
        with self.lock, open(self.path, "a", encoding="utf8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def entries(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf8").splitlines() if l.strip()]


MANIFEST = Manifest(DATA / "crawl_manifest.jsonl")


# ───────────────────────────── HTTP fetcher ─────────────────────────────
@dataclass
class Response:
    url: str
    final_url: str
    status: int
    content: bytes
    headers: Dict[str, str]
    fetched_at: str
    from_cache: bool = False
    content_sha256: str = ""

    @property
    def text(self) -> str:
        return self.content.decode("utf8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.content.decode("utf8"))

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class BlockedByRobots(Exception):
    pass


class Fetcher:
    """Polite, cached HTTP client.

    * robots.txt is consulted per host (missing robots = allowed); disallowed URLs are never fetched.
    * Per-host spacing (config delay or robots crawl-delay, whichever is larger).
    * Exponential backoff retries for timeouts/429/5xx, honouring Retry-After.
    * Disk cache with ETag/Last-Modified revalidation for incremental re-runs.
    """

    def __init__(self, config: CrawlConfig = CONFIG):
        self.cfg = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.user_agent
        self.robots: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}
        self.robots_raw: Dict[str, Dict[str, Any]] = {}
        self.host_locks: Dict[str, threading.Lock] = {}
        self.host_last: Dict[str, float] = {}
        self.glock = threading.Lock()
        self.listeners: Dict[str, Any] = {}  # source_id -> callable(event dict, Response|None)
        self.extra_allow: set = set()
        self.ssrf_checked: Dict[str, bool] = {}
        (CACHE / "http").mkdir(parents=True, exist_ok=True)

    def _emit(self, source_id: str, event: Dict[str, Any], resp: "Optional[Response]" = None) -> None:
        MANIFEST.log(dict(event))
        cb = self.listeners.get(source_id)
        if cb is not None:
            cb(event, resp)  # may raise JobCancelled

    def _host_allowed(self, host: str) -> bool:
        domains = tuple(self.cfg.allow_domains) + tuple(self.extra_allow)
        return any(host == d or host.endswith("." + d) for d in domains)

    def _safe(self, host: str) -> bool:
        if host not in self.ssrf_checked:
            self.ssrf_checked[host] = is_public_host(host)
        return self.ssrf_checked[host]

    # robots ---------------------------------------------------------------
    def _robots(self, url: str) -> Optional[urllib.robotparser.RobotFileParser]:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        with self.glock:
            if base in self.robots:
                return self.robots[base]
        rp: Optional[urllib.robotparser.RobotFileParser] = None
        info: Dict[str, Any] = {"robots_url": base + "/robots.txt", "checked_at": now_iso()}
        try:
            r = self.session.get(base + "/robots.txt", timeout=self.cfg.timeout)
            info["status"] = r.status_code
            if r.status_code == 200 and "text/html" not in r.headers.get("content-type", ""):
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(r.text.splitlines())
                info["excerpt"] = "\n".join(l for l in r.text.splitlines() if l.strip())[:1500]
            else:
                info["note"] = "No robots.txt (treated as allow-all per RFC 9309)"
        except Exception as e:  # network failure on robots -> conservative: still allow but record
            info["error"] = str(e)
        with self.glock:
            self.robots[base] = rp
            self.robots_raw[base] = info
        return rp

    def allowed(self, url: str) -> bool:
        rp = self._robots(url)
        return True if rp is None else rp.can_fetch(self.cfg.user_agent, url)

    def _delay_for(self, host: str, url: str) -> float:
        rp = self._robots(url)
        cd = None
        if rp is not None:
            try:
                cd = rp.crawl_delay(self.cfg.user_agent)
            except Exception:
                cd = None
        return max(self.cfg.per_host_delay, float(cd or 0))

    def _wait_turn(self, host: str, url: str) -> threading.Lock:
        with self.glock:
            lock = self.host_locks.setdefault(host, threading.Lock())
        lock.acquire()
        delay = self._delay_for(host, url)
        elapsed = time.time() - self.host_last.get(host, 0)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        return lock

    # cache ----------------------------------------------------------------
    def _cache_paths(self, url: str) -> Tuple[Path, Path]:
        k = sha256(url.encode())
        return CACHE / "http" / f"{k}.body", CACHE / "http" / f"{k}.meta.json"

    def _cached(self, url: str) -> Optional[Tuple[Dict[str, Any], bytes]]:
        body, meta = self._cache_paths(url)
        if body.exists() and meta.exists():
            return json.loads(meta.read_text()), body.read_bytes()
        return None

    # main -----------------------------------------------------------------
    def get(self, url: str, *, source_id: str, parent: Optional[str] = None, depth: int = 0,
            headers: Optional[Dict[str, str]] = None, check_robots: bool = True, refresh: bool = False,
            timeout: Optional[float] = None, retries: Optional[int] = None) -> Optional[Response]:
        host = host_of(url)
        base_log = {"url": url, "source_id": source_id, "parent": parent, "depth": depth}
        if urlparse(url).scheme not in ("http", "https"):
            self._emit(source_id, {**base_log, "outcome": "skipped_scheme"})
            return None
        if not self._host_allowed(host):
            self._emit(source_id, {**base_log, "outcome": "skipped_not_allowlisted"})
            return None
        if any(re.search(p, url) for p in self.cfg.deny_patterns):
            self._emit(source_id, {**base_log, "outcome": "skipped_denylist"})
            return None
        if not self._safe(host):
            self._emit(source_id, {**base_log, "outcome": "blocked_unsafe_destination"})
            return None
        if check_robots and not self.allowed(url):
            self._emit(source_id, {**base_log, "outcome": "blocked_robots"})
            return None

        cached = self._cached(url)
        req_headers = dict(headers or {})
        if cached and not (self.cfg.refresh or refresh):
            meta, body = cached
            age_h = (time.time() - meta.get("_epoch", 0)) / 3600
            if age_h < self.cfg.cache_ttl_hours:
                resp = Response(url, meta["final_url"], meta["status"], body, meta.get("headers", {}), meta["fetched_at"], True, meta.get("content_sha256", ""))
                self._emit(source_id, {**base_log, "outcome": "cache_hit", "status": meta["status"], "final_url": meta["final_url"], "bytes": len(body), "content_sha256": meta.get("content_sha256")}, resp)
                return resp
            if meta.get("etag"):
                req_headers["If-None-Match"] = meta["etag"]
            if meta.get("last_modified"):
                req_headers["If-Modified-Since"] = meta["last_modified"]

        last_err = None
        max_retries = self.cfg.retries if retries is None else retries
        for attempt in range(max_retries + 1):
            lock = self._wait_turn(host, url)
            try:
                r = self._get_following_safe_redirects(url, req_headers, timeout)
                chunks, size = [], 0
                for chunk in r.iter_content(65536):
                    size += len(chunk)
                    if size > self.cfg.max_bytes:
                        r.close()
                        raise ValueError(f"response exceeds max_bytes ({self.cfg.max_bytes})")
                    chunks.append(chunk)
                content = b"".join(chunks)
            except Exception as e:
                last_err = str(e)
                self.host_last[host] = time.time()
                lock.release()
                if "max_bytes" in last_err or isinstance(e, UnsafeDestination):
                    break
                time.sleep(self.cfg.backoff_base ** attempt)
                continue
            self.host_last[host] = time.time()
            lock.release()

            if r.status_code == 304 and cached:
                meta, body = cached
                meta["_epoch"] = time.time()
                self._cache_paths(url)[1].write_text(json.dumps(meta))
                resp = Response(url, meta["final_url"], meta["status"], body, meta.get("headers", {}), meta["fetched_at"], True, meta.get("content_sha256", ""))
                self._emit(source_id, {**base_log, "outcome": "not_modified", "status": 304, "final_url": meta["final_url"], "bytes": len(body), "content_sha256": meta.get("content_sha256")}, resp)
                return resp
            if r.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                ra = r.headers.get("Retry-After")
                wait = float(ra) if ra and ra.isdigit() else self.cfg.backoff_base ** (attempt + 1)
                self._emit(source_id, {**base_log, "outcome": "retry", "status": r.status_code, "wait_s": wait})
                time.sleep(min(wait, 60))
                continue

            fetched = now_iso()
            h = {k.lower(): v for k, v in r.headers.items() if k.lower() in ("content-type", "etag", "last-modified", "x-ratelimit-remaining", "x-ratelimit-limit",
                                                                     "x-ratelimit-reset", "x-ratelimit-resource", "x-ratelimit-used", "retry-after", "link")}
            digest = sha256(content)
            meta = {"url": url, "final_url": r.url, "status": r.status_code, "fetched_at": fetched, "_epoch": time.time(),
                    "headers": h, "etag": r.headers.get("ETag"), "last_modified": r.headers.get("Last-Modified"), "content_sha256": digest}
            if r.status_code == 200:
                bp, mp = self._cache_paths(url)
                bp.write_bytes(content)
                mp.write_text(json.dumps(meta))
            resp = Response(url, r.url, r.status_code, content, h, fetched, False, digest)
            self._emit(source_id, {**base_log, "outcome": "fetched" if r.ok else "http_error", "status": r.status_code, "final_url": r.url,
                                   "bytes": len(content), "content_sha256": digest, "content_type": h.get("content-type")}, resp)
            return resp

        self._emit(source_id, {**base_log, "outcome": "failed", "error": last_err})
        return None

    def _get_following_safe_redirects(self, url: str, headers: Dict[str, str], timeout: Optional[float] = None, max_hops: int = 5):
        """Follow redirects manually so every hop is re-validated (scheme, allow-list, public IP)."""
        current = url
        for _ in range(max_hops + 1):
            r = self.session.get(current, headers=headers, timeout=timeout or self.cfg.timeout, stream=True, allow_redirects=False)
            if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
                loc = r.headers.get("Location")
                r.close()
                if not loc:
                    raise ValueError("redirect without Location")
                from urllib.parse import urljoin as _uj
                nxt = _uj(current, loc)
                h = host_of(nxt)
                if urlparse(nxt).scheme not in ("http", "https") or not self._host_allowed(h) or not self._safe(h):
                    raise UnsafeDestination(f"redirect to disallowed destination {nxt}")
                current = nxt
                continue
            return r
        raise ValueError("too many redirects")


FETCHER = Fetcher()


# ───────────────────────────── GitHub ─────────────────────────────
class GitHub:
    """GitHub access.

    * REST API (metadata/trees) with optional token auth (`Authorization: Bearer …`, never logged or cached in keys),
      `X-GitHub-Api-Version`, conditional requests via the fetcher cache, rate-limit header capture, waiting on primary
      limits (bounded), back-off on secondary limits, Link-header pagination.
    * File contents via raw.githubusercontent.com (no API quota) pinned to the inspected commit SHA.
    """

    API = "https://api.github.com"
    API_VERSION = "2022-11-28"
    MAX_WAIT_S = 90

    def __init__(self, fetcher: Fetcher = FETCHER):
        self.f = fetcher
        self.token = os.environ.get("GITHUB_TOKEN")  # set by the backend from its secret settings; never written to outputs
        self.on_usage = None  # optional callback(dict) for telemetry (no credentials included)
        self.state: Dict[str, Any] = {"remaining": None, "limit": None, "reset": None, "resource": None}
        self.lock = threading.Lock()
        self.calls = 0

    @property
    def authenticated(self) -> bool:
        return bool(self.token)

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": self.API_VERSION}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _record(self, path: str, r: "Optional[Response]", outcome: str) -> None:
        hd = (r.headers if r is not None else {}) or {}
        def _i(k):
            try:
                return int(hd[k])
            except (KeyError, TypeError, ValueError):
                return None
        with self.lock:
            if _i("x-ratelimit-remaining") is not None and not (r is not None and r.from_cache):
                self.state.update(remaining=_i("x-ratelimit-remaining"), limit=_i("x-ratelimit-limit"), reset=_i("x-ratelimit-reset"),
                                  resource=hd.get("x-ratelimit-resource"))
        if self.on_usage:
            try:
                self.on_usage({"provider": "github", "endpoint": path, "status": r.status if r is not None else None, "outcome": outcome,
                               "authenticated": self.authenticated, "rate_limit": _i("x-ratelimit-limit"), "rate_remaining": _i("x-ratelimit-remaining"),
                               "rate_reset": _i("x-ratelimit-reset"), "rate_resource": hd.get("x-ratelimit-resource"), "retry_after_s": _i("retry-after"),
                               "from_cache": bool(r is not None and r.from_cache)})
            except Exception:
                pass

    def _gate(self, path: str) -> Optional[Dict[str, Any]]:
        """Before a network call: if the primary quota is exhausted, wait (bounded) or refuse without calling."""
        with self.lock:
            rem, reset = self.state.get("remaining"), self.state.get("reset")
        if rem is not None and rem <= 0 and reset:
            wait = reset - time.time() + 1
            if wait > self.MAX_WAIT_S:
                self._record(path, None, "skipped_rate_limited")
                return {"_error": "rate_limited", "reset": reset, "wait_s": int(wait)}
            if wait > 0:
                time.sleep(wait)
        return None

    def _api(self, path: str, source_id: str) -> Optional[Any]:
        blocked = self._gate(path)
        if blocked:
            return blocked
        for attempt in range(2):
            r = self.f.get(self.API + path, source_id=source_id, headers=self._headers(), check_robots=False, retries=1)
            self.calls += 0 if (r is not None and r.from_cache) else 1
            if r is None:
                self._record(path, None, "failed")
                return {"_error": "failed"}
            if r.ok:
                self._record(path, r, "cache_hit" if r.from_cache else "ok")
                return r.json()
            body = r.text[:500].lower()
            if r.status in (403, 429) and (r.headers.get("x-ratelimit-remaining") == "0"):
                self._record(path, r, "primary_rate_limited")
                blocked = self._gate(path)
                if blocked:
                    return blocked
                continue
            if r.status in (403, 429) and ("secondary rate limit" in body or r.headers.get("retry-after")):
                ra = int(r.headers.get("retry-after") or 60)
                self._record(path, r, "secondary_rate_limited")
                if ra > self.MAX_WAIT_S or attempt:
                    return {"_error": "secondary_rate_limited", "retry_after_s": ra}
                time.sleep(ra)
                continue
            self._record(path, r, "unauthorized" if r.status == 401 else "http_error")
            return {"_error": r.status}
        return {"_error": "rate_limited"}

    def paginate(self, path: str, source_id: str, max_pages: int = 10) -> List[Any]:
        """Follow `Link: rel="next"` up to max_pages (per_page=100)."""
        out: List[Any] = []
        url = path + ("&" if "?" in path else "?") + "per_page=100"
        for _ in range(max_pages):
            blocked = self._gate(url)
            if blocked:
                break
            r = self.f.get(self.API + url, source_id=source_id, headers=self._headers(), check_robots=False, retries=1)
            if r is None or not r.ok:
                self._record(url, r, "failed" if r is None else "http_error")
                break
            self._record(url, r, "cache_hit" if r.from_cache else "ok")
            data = r.json()
            out.extend(data if isinstance(data, list) else data.get("items", []))
            m = re.search(r'<https://api\.github\.com([^>]+)>;\s*rel="next"', r.headers.get("link") or "")
            if not m:
                break
            url = m.group(1)
        return out

    def meta(self, full: str, source_id: str) -> Dict[str, Any]:
        """Single-call repository metadata (license, default branch, activity)."""
        m = self._api(f"/repos/{full}", source_id) or {}
        if "_error" in m:
            return {"full_name": full, "error": m["_error"]}
        return {"full_name": m.get("full_name"), "html_url": m.get("html_url"), "license": (m.get("license") or {}).get("spdx_id"),
                "default_branch": m.get("default_branch"), "archived": m.get("archived"), "pushed_at": m.get("pushed_at"), "stars": m.get("stargazers_count"),
                "description": m.get("description"), "homepage": m.get("homepage")}

    def repo(self, full: str, source_id: str) -> Dict[str, Any]:
        meta = self._api(f"/repos/{full}", source_id) or {}
        if "_error" in meta or "message" in meta:
            return {"full_name": full, "error": meta.get("_error") or meta.get("message")}
        branch = meta.get("default_branch", "main")
        commit = self._api(f"/repos/{full}/commits/{branch}", source_id) or {}
        sha = commit.get("sha")
        tree = self._api(f"/repos/{full}/git/trees/{sha or branch}?recursive=1", source_id) or {}
        return {
            "full_name": meta.get("full_name", full),
            "html_url": meta.get("html_url"),
            "description": meta.get("description"),
            "default_branch": branch,
            "commit_sha": sha,
            "commit_date": ((commit.get("commit") or {}).get("committer") or {}).get("date"),
            "license": (meta.get("license") or {}).get("spdx_id"),
            "language": meta.get("language"),
            "stars": meta.get("stargazers_count"),
            "forks": meta.get("forks_count"),
            "open_issues": meta.get("open_issues_count"),
            "archived": meta.get("archived"),
            "pushed_at": meta.get("pushed_at"),
            "topics": meta.get("topics", []),
            "homepage": meta.get("homepage"),
            "tree_truncated": tree.get("truncated"),
            "paths": [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob"],
        }

    def raw(self, full: str, ref: str, path: str, source_id: str, parent: Optional[str] = None) -> Optional[str]:
        from urllib.parse import quote
        url = f"https://raw.githubusercontent.com/{full}/{ref}/{quote(path)}"
        r = self.f.get(url, source_id=source_id, parent=parent, depth=1)
        return r.text if r is not None and r.ok else None

    @staticmethod
    def blob_url(full: str, ref: str, path: str) -> str:
        from urllib.parse import quote
        return f"https://github.com/{full}/blob/{ref}/{quote(path)}"


GITHUB = GitHub()


def npm_latest(pkg: str, source_id: str) -> Optional[str]:
    r = FETCHER.get(f"https://registry.npmjs.org/{pkg}/latest", source_id=source_id, check_robots=False)
    try:
        return r.json().get("version") if r and r.ok else None
    except Exception:
        return None


# ───────────────────────────── records ─────────────────────────────
TYPE_PREFIX = {
    "system": "sys", "component": "cmp", "token": "tok", "pattern": "pat", "guideline": "gdl", "tool": "tool",
    "specification": "spec", "repository": "repo", "resource": "res", "comparison": "cmpr",
}


def record_id(record_type: str, source_id: str, key: str) -> str:
    return f"{TYPE_PREFIX[record_type]}:{source_id.lower()}:{slugify(key, 120)}"


def make_record(record_type: str, source_id: str, key: str, title: str, *, summary: Optional[str] = None,
                primary_category: str, source_url: str, extraction_method: str, source_status: str = "unknown",
                **kw: Any) -> Dict[str, Any]:
    rec = {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id(record_type, source_id, key),
        "record_type": record_type,
        "title": title,
        "summary": summary,
        "primary_category": primary_category,
        "secondary_categories": [],
        "tags": [],
        "organization": None,
        "design_system": None,
        "source_id": source_id,
        "source_url": source_url,
        "canonical_url": canonical_url(source_url),
        "repository_url": None,
        "source_file_path": None,
        "source_section": None,
        "source_version": None,
        "source_status": source_status,
        "extraction_method": extraction_method,
        "evidence_excerpt": None,
        "normalized_content": {},
        "frameworks": [],
        "platforms": [],
        "technologies": [],
        "license": None,
        "confidence": "medium",
        "verification_status": "unverified",
        "last_verified_at": now_iso(),
        "relationships": [],
        "duplicate_group_id": None,
        "notes": [],
    }
    for k, v in kw.items():
        rec[k] = v
    return rec


def excerpt(text: Optional[str], n: int = 300) -> Optional[str]:
    if not text:
        return None
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


# ───────────────────────────── Markdown helpers ─────────────────────────────
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def md_sections(text: str) -> List[Dict[str, Any]]:
    """Split Markdown into heading-scoped sections (code fences respected). Each has a heading path."""
    out: List[Dict[str, Any]] = []
    stack: List[Tuple[int, str]] = []
    cur = {"level": 0, "title": "", "path": [], "lines": []}
    fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
        m = None if fence else HEADING.match(line)
        if m:
            out.append(cur)
            lvl, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            stack.append((lvl, title))
            cur = {"level": lvl, "title": title, "path": [t for _, t in stack], "lines": []}
        else:
            cur["lines"].append(line)
    out.append(cur)
    for s in out:
        s["body"] = "\n".join(s.pop("lines"))
    return [s for s in out if s["title"] or s["body"].strip()]


def _split_row(line: str) -> List[str]:
    """Split a Markdown table row on pipes that are not escaped and not inside backticks."""
    cells, buf, tick = [], [], False
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if c == "`":
            tick = not tick
        if c == "|" and not tick:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def md_tables(body: str) -> List[Dict[str, Any]]:
    tables, lines, i = [], body.splitlines(), 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", lines[i + 1]):
            header = [clean_cell(h) for h in _split_row(lines[i])]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = [clean_cell(c) for c in _split_row(lines[j])]
                rows.append(dict(zip(header, cells)))
                j += 1
            tables.append({"header": header, "rows": rows})
            i = j
        else:
            i += 1
    return tables


def clean_cell(c: str) -> str:
    c = c.replace("&#xA;", " ").replace("<br>", " ").replace("<br/>", " ")
    c = re.sub(r"\s+", " ", c).strip()
    if len(c) >= 2 and c.startswith("`") and c.endswith("`") and c.count("`") == 2:
        c = c[1:-1]
    return c


def classify_table(header: List[str]) -> str:
    h = [x.lower() for x in header]
    hs = " ".join(h)
    if any(x in ("prop", "property", "name", "props", "参数") for x in h[:1]) and ("type" in hs or "description" in hs):
        return "props"
    if h and ("key" in h[0] or "shortcut" in h[0] or "keys" in h[0]):
        return "keyboard"
    if h and "attribute" in h[0]:
        return "data_attributes"
    if h and ("css variable" in hs or h[0].startswith("variable") or h[0].startswith("--")):
        return "css_variables"
    if h and ("selector" in h[0] or "classname" in hs.replace(" ", "")):
        return "styles_api"
    if "token" in hs:
        return "tokens"
    return "other"


def norm_prop(row: Dict[str, str]) -> Dict[str, Optional[str]]:
    get = lambda *ks: next((row[k] for k in row if k.lower() in ks and row[k] not in ("", "-", "—")), None)  # noqa: E731
    return {
        "name": (get("prop", "property", "name", "props") or "").strip("`") or None,
        "type": get("type"),
        "default": get("default", "default value"),
        "description": get("description"),
        "required": get("required"),
        "since_version": get("version"),
    }


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf8").splitlines() if l.strip()]
