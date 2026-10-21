"""Storybook showcase enumeration and per-component variant extraction.

Per project (checkpointed):
  1. Resolve the published Storybook URL (redirects re-validated by the fetcher).
  2. Read the public story index: `index.json` (Storybook ≥7) or `stories.json` (6.x, when enabled). Raw index is stored
     content-addressed. No story URL is guessed: IDs come from the index; URLs use Storybook's documented `?path=` scheme.
  3. Optional `project.json` → Storybook version / renderer.
  4. If the project's GitHub repository is known, fetch up to N story source files (paths from the index `importPath`)
     from raw.githubusercontent.com and parse CSF `args` / `argTypes` literally → verified variant data.
  5. When no source is available, non-generic story names yield *inferred* variants (method story_name_inference, low confidence).
  6. Stories are linked to canonical components only by exact name within the project's resolved system; otherwise unresolved."""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..database.session import SessionLocal
from ..models import Component, DesignSystem, RawDocument, Record, Source, StorybookProject, StorybookStory, StorybookVariant
from ..scrapers.dskb import core as engine
from ..scrapers.dskb.adapters.repos import js_object_to_python
from .storage import storage

TAG = "SB"
GENERIC_NAMES = {"default", "basic", "playground", "example", "examples", "overview", "docs", "documentation", "primary story", "template", "usage", "demo", "all", "story"}
MAX_SOURCE_FILES = 12


def now():
    return datetime.now(timezone.utc)


def start_case(export_name: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", export_name)
    s = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", s)
    return re.sub(r"[_\s]+", " ", s).strip()


def _balanced(src: str, start: int) -> str | None:
    """Return the {...} block starting at src[start] == '{' (string/comment aware)."""
    if start >= len(src) or src[start] != "{":
        return None
    depth, i, q = 0, start, None
    while i < len(src):
        c = src[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "\"'`":
            q = c
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = j if j != -1 else len(src)
            continue
        elif src.startswith("/*", i):
            j = src.find("*/", i)
            i = j + 2 if j != -1 else len(src)
            continue
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return None


def _prop_block(obj: str, key: str) -> str | None:
    m = re.search(r"(?<![\w$])%s\s*:\s*\{" % re.escape(key), obj)
    return _balanced(obj, m.end() - 1) if m else None


def _literal(block: str | None) -> Any:
    """Parse an object literal; on failure keep only simple literal pairs (strings/numbers/booleans/arrays of literals)."""
    if not block:
        return None
    try:
        return js_object_to_python("export default " + block)
    except Exception:
        out: dict[str, Any] = {}
        for m in re.finditer(r"([\w$]+|\"[^\"]+\"|'[^']+')\s*:\s*(\"[^\"]*\"|'[^']*'|-?\d+(?:\.\d+)?|true|false|null|\[[^\[\]{}]*\])\s*(?=,|\n|\})", block):
            k = m.group(1).strip("\"'")
            v = m.group(2)
            try:
                out[k] = js_object_to_python("export default {v: " + v + "}")["v"]
            except Exception:
                out[k] = v
        out["_partial_parse"] = True
        return out


def parse_csf(src: str) -> dict[str, Any]:
    meta_block = None
    m = re.search(r"export\s+default\s+\{", src)
    if m:
        meta_block = _balanced(src, m.end() - 1)
    else:
        m = re.search(r"const\s+meta\s*(?::[^=]+)?=\s*\{", src)
        if m:
            meta_block = _balanced(src, m.end() - 1)
    meta = {"args": _literal(_prop_block(meta_block, "args")) if meta_block else None,
            "argTypes": _literal(_prop_block(meta_block, "argTypes")) if meta_block else None}
    stories: dict[str, dict[str, Any]] = {}
    for m in re.finditer(r"export\s+const\s+([A-Z][\w$]*)\s*(?::[^=]+)?=\s*(\{|\(|[\w$.]+\.bind|\w)", src):
        name = m.group(1)
        block = _balanced(src, m.end() - 1) if m.group(2) == "{" else None
        args = _literal(_prop_block(block, "args")) if block else None
        argt = _literal(_prop_block(block, "argTypes")) if block else None
        stories[name] = {"args": args, "argTypes": argt}
    for m in re.finditer(r"^([A-Z][\w$]*)\.args\s*=\s*\{", src, re.M):  # CSF2
        stories.setdefault(m.group(1), {})["args"] = _literal(_balanced(src, m.end() - 1))
    return {"meta": meta, "stories": stories}


def _store_raw(db: Session, content: bytes, url: str, ctype: str | None) -> int:
    sha = engine.sha256(content)
    key = storage().put(f"raw/{sha[:2]}/{sha}", content)
    stmt = insert(RawDocument).values(content_sha256=sha, storage_key=key, content_type=ctype, size_bytes=len(content), first_url=url)
    return db.execute(stmt.on_conflict_do_update(index_elements=["content_sha256"], set_={"storage_key": stmt.excluded.storage_key}).returning(RawDocument.id)).scalar_one()


# ───────────────────────────── registry ─────────────────────────────
def refresh_registry(db: Session) -> dict[str, Any]:
    """Re-read the public showcase catalog and reconcile with stored projects (added/removed/changed)."""
    r = engine.FETCHER.get("https://storybook.js.org/showcase", source_id=TAG, refresh=True)
    catalog = {}
    if r and r.ok:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        if m:
            for p in json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("projects", []):
                catalog[p["slug"]] = p
    s04 = db.scalar(select(Source.id).where(Source.key == "S04"))
    known = {p.slug: p for p in db.scalars(select(StorybookProject))}
    recs = {r.record_key.split(":", 2)[2]: r for r in db.scalars(select(Record).where(Record.source_id == s04, Record.record_type == "system"))}
    added, removed, changed = [], [], []
    for slug, p in catalog.items():
        rec = recs.get(slug)
        nc = (rec.content if rec else {}) or {}
        sb_url = nc.get("storybook_url")
        repo = nc.get("repository_url")
        if not rec:  # new to the catalog since the last S04 crawl → fetch its detail page
            d = engine.FETCHER.get(f"https://storybook.js.org/showcase/{slug}", source_id=TAG)
            if d and d.ok:
                mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', d.text, re.S)
                pp = json.loads(mm.group(1)).get("props", {}).get("pageProps", {}) if mm else {}
                sb_url, repo = pp.get("storybookUrl"), pp.get("gitHubUrl")
        row = known.get(slug)
        if row is None:
            row = StorybookProject(slug=slug, title=p.get("title") or slug, organization=p.get("org"), storybook_url=sb_url, repository_url=repo,
                                   showcase_record_key=rec.record_key if rec else None, status="pending")
            db.add(row)
            if slug not in recs:
                added.append(slug)
        else:
            if row.storybook_url != sb_url and sb_url:
                changed.append({"slug": slug, "field": "storybook_url", "old": row.storybook_url, "new": sb_url})
                row.storybook_url = sb_url
            row.repository_url = repo or row.repository_url
    for slug in set(recs) - set(catalog):
        removed.append(slug)
        if slug in known:
            known[slug].limitation = "No longer listed in the Storybook showcase catalog."
    db.flush()
    return {"catalog_projects": len(catalog), "previously_crawled": len(recs), "added": sorted(added), "removed_from_catalog": sorted(removed), "changed": changed}


# ───────────────────────────── per project ─────────────────────────────
def _system_for(db: Session, project: StorybookProject) -> tuple[str | None, int | None]:
    if not project.showcase_record_key:
        return None, None
    rid = db.scalar(select(Record.system_id).where(Record.record_key == project.showcase_record_key))
    if not rid:
        return None, None
    key = db.scalar(select(DesignSystem.key).where(DesignSystem.id == rid))
    return key, rid


def process_project(project_id: int) -> dict[str, Any]:
    with SessionLocal() as db:
        p = db.get(StorybookProject, project_id)
        res = {"slug": p.slug, "requests_failed": 0}
        p.last_checked_at = now()
        if not p.storybook_url:
            p.status, p.limitation, p.retry_eligible = "no_storybook_url", "The showcase does not list a Storybook URL for this project.", False
            db.commit()
            return res
        engine.FETCHER.extra_allow.add(urlparse(p.storybook_url).netloc.lower())
        r = engine.FETCHER.get(p.storybook_url, source_id=TAG)
        if not r or not r.ok:
            p.status, p.failed_requests = "unreachable", p.failed_requests + 1
            p.limitation = f"Storybook URL did not respond successfully ({r.status if r else 'no response: offline, blocked by robots/SSRF policy or network'})."
            p.retry_eligible = True
            db.commit()
            return res
        final = r.final_url.split("?")[0].split("#")[0]
        final = re.sub(r"(index|iframe)\.html$", "", final)
        base = final if final.endswith("/") else final + "/"
        engine.FETCHER.extra_allow.add(urlparse(base).netloc.lower())
        p.resolved_url = base
        idx, kind = None, None
        for name, k in (("index.json", "index.json"), ("stories.json", "stories.json")):
            ir = engine.FETCHER.get(urljoin(base, name), source_id=TAG, parent=base)
            if ir and ir.ok:
                try:
                    data = json.loads(ir.content)
                    if isinstance(data, dict) and ("entries" in data or "stories" in data):
                        idx, kind = (data, k)
                        p.raw_index_document_id = _store_raw(db, ir.content, ir.final_url, ir.headers.get("content-type"))
                        p.index_sha256 = engine.sha256(ir.content)
                        break
                except ValueError:
                    pass
            else:
                res["requests_failed"] += 1
        pj = engine.FETCHER.get(urljoin(base, "project.json"), source_id=TAG, parent=base)
        if pj and pj.ok:
            try:
                d = json.loads(pj.content)
                p.storybook_version = str(d.get("storybookVersion") or d.get("storybookVersionSpecifier") or "") or None
                p.framework = (d.get("framework") or {}).get("name") if isinstance(d.get("framework"), dict) else d.get("framework") or d.get("renderer")
            except ValueError:
                pass
        if idx is None:
            p.status, p.index_kind = "no_public_index", None
            p.limitation = "Neither index.json nor stories.json is publicly exposed; stories cannot be enumerated without executing the Storybook UI (browser rendering not used)."
            p.retry_eligible = False
            db.commit()
            return res
        p.index_kind = kind
        if not p.storybook_version and kind == "index.json":
            p.storybook_version = f"≥7 (index v{idx.get('v')})"
        entries = idx.get("entries") if "entries" in idx else idx.get("stories", {})
        sys_key, sys_id = _system_for(db, p)
        p.system_key = sys_key
        comps = {}
        if sys_id:
            comps = {c.name.lower(): c.id for c in db.scalars(select(Component).where(Component.system_id == sys_id))}
        stories, docs = 0, 0
        story_rows: dict[str, StorybookStory] = {}
        for eid, e in entries.items():
            etype = e.get("type") or ("docs" if (e.get("parameters") or {}).get("docsOnly") else "story")
            tags = e.get("tags") or []
            if etype == "docs" and "autodocs" in tags:
                etype = "autodocs"
            title, name = e.get("title") or e.get("kind") or "", e.get("name") or e.get("story") or eid
            comp_name = title.split("/")[-1].strip() if title else None
            url = urljoin(base, f"?path=/{'docs' if etype in ('docs', 'autodocs') else 'story'}/{eid}")
            cid = comps.get((comp_name or "").lower())
            vals = dict(project_id=p.id, entry_id=eid, entry_type=etype, title=title, name=name, export_name=e.get("exportName"), component_name=comp_name,
                        component_id=cid, resolution_status="linked" if cid else ("not_applicable" if etype in ("docs",) else "unresolved"),
                        tags=tags, import_path=e.get("importPath"), story_url=url, extraction_status="index_only",
                        evidence=[{"type": "story_index", "url": urljoin(base, kind), "sha256": p.index_sha256}], last_verified_at=now())
            stmt = insert(StorybookStory).values(story_key=f"{p.slug}::{eid}", **vals)
            sid = db.execute(stmt.on_conflict_do_update(index_elements=["story_key"], set_=vals).returning(StorybookStory.id)).scalar_one()
            if etype == "story":
                stories += 1
                story_rows[eid] = (sid, e)
            else:
                docs += 1
        # ── source parsing for args/argTypes ──
        variants = 0
        files_ok = 0
        m = re.match(r"https?://github\.com/([\w.-]+)/([\w.-]+)", p.repository_url or "")
        parsed_by_path: dict[str, dict] = {}
        if m:
            owner, repo = m.group(1), m.group(2).removesuffix(".git")
            paths = []
            for eid, (sid, e) in story_rows.items():
                ip = (e.get("importPath") or "").lstrip("./")
                if ip and ip not in paths and not ip.endswith(".mdx"):
                    paths.append(ip)
            misses = 0
            for ip in paths[:MAX_SOURCE_FILES]:
                if misses >= 4 and not files_ok:
                    break
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{ip}"
                fr = engine.FETCHER.get(url, source_id=TAG)
                if not fr or not fr.ok:
                    misses += 1
                    res["requests_failed"] += 1
                    continue
                files_ok += 1
                parsed_by_path[ip] = {"url": url, **parse_csf(fr.text[:400_000])}
        for eid, (sid, e) in story_rows.items():
            ip = (e.get("importPath") or "").lstrip("./")
            parsed = parsed_by_path.get(ip)
            st = db.get(StorybookStory, sid)
            if parsed:
                exp = e.get("exportName") or next((k for k in parsed["stories"] if start_case(k).lower() == (st.name or "").lower()), None)
                sdata = parsed["stories"].get(exp or "", {})
                meta_args = parsed["meta"].get("args") if isinstance(parsed["meta"].get("args"), dict) else {}
                story_args = sdata.get("args") if isinstance(sdata.get("args"), dict) else {}
                merged_args = {**(meta_args or {}), **(story_args or {})} or None
                argt = {**(parsed["meta"].get("argTypes") or {}), **(sdata.get("argTypes") or {})} if isinstance(parsed["meta"].get("argTypes") or {}, dict) else None
                st.export_name, st.args, st.arg_types = exp or st.export_name, merged_args, argt or None
                st.source_file_url = parsed["url"]
                st.extraction_status = "source_parsed" if exp else "source_unmatched"
                st.evidence = st.evidence + [{"type": "story_source", "url": parsed["url"], "export": exp}]
                if story_args:
                    variants += _variant(db, st, p, f"{st.title} / {st.name}", {k: v for k, v in story_args.items() if k != "_partial_parse"}, "story_args", "high",
                                         [{"source_file": parsed["url"], "export": exp}, {"story_url": st.story_url}])
                for prop, spec in (argt or {}).items():
                    if isinstance(spec, dict):
                        opts = spec.get("options") or ((spec.get("control") or {}).get("options") if isinstance(spec.get("control"), dict) else None)
                        if isinstance(opts, list) and opts:
                            variants += _variant(db, st, p, f"{st.component_name or st.title}: {prop} options", {prop: opts}, "arg_types_options", "high",
                                                 [{"source_file": parsed["url"], "argType": prop}])
            elif (st.name or "").strip().lower() not in GENERIC_NAMES:
                variants += _variant(db, st, p, f"{st.title} / {st.name}", {"story_name": st.name}, "story_name_inference", "low",
                                     [{"story_index": urljoin(base, kind), "note": "Variant label inferred from the story name only; not an API capability claim."}])
        p.stories_discovered = stories + docs
        p.stories_extracted = stories
        p.docs_entries = docs
        p.source_files_parsed = files_ok
        p.variants_extracted = db.scalar(select(func.count()).select_from(StorybookVariant).where(StorybookVariant.project_id == p.id)) or 0
        p.failed_requests = res["requests_failed"]
        p.status = "indexed" if stories or docs else "empty_index"
        p.limitation = None if files_ok else ("No public GitHub repository listed; args/argTypes not available without executing the Storybook." if not m
                                               else "Story source files not found at the index importPath in the repository default branch (monorepo layout or private sources).")
        p.retry_eligible = False
        db.commit()
        res.update(stories=stories, docs=docs, variants=p.variants_extracted, files=files_ok)
        return res


def _variant(db: Session, st: StorybookStory, p: StorybookProject, label: str, props: dict, method: str, confidence: str, evidence: list) -> int:
    key = f"{st.story_key}::{method}::{engine.sha256(json.dumps(props, sort_keys=True, default=str).encode())[:12]}"
    vals = dict(story_id=st.id, project_id=p.id, component_id=st.component_id, component_name=st.component_name, label=label[:2000], props=props,
                method=method, confidence=confidence, evidence=evidence)
    stmt = insert(StorybookVariant).values(variant_key=key, **vals)
    db.execute(stmt.on_conflict_do_update(index_elements=["variant_key"], set_=vals))
    return 1


def run_all(db: Session, progress: Callable[[int, int, str], None] | None = None, refresh: bool = False, workers: int = 6) -> dict[str, Any]:
    reg = refresh_registry(db)
    db.commit()
    q = select(StorybookProject.id)
    if not refresh:
        q = q.where(StorybookProject.status.in_(["pending", "unreachable"]))
    ids = list(db.scalars(q.order_by(StorybookProject.slug)))
    done = 0
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(_safe, ids):
            done += 1
            results.append(r)
            if progress:
                progress(done, len(ids), f"{r.get('slug')}: {r.get('error') or r.get('stories', 0)} stories")
    return {"registry": reg, "projects_processed": len(results), "errors": [r for r in results if r.get("error")][:50]}


def _safe(pid: int) -> dict[str, Any]:
    try:
        return process_project(pid)
    except Exception as e:  # one project must not stop the others
        with SessionLocal() as db:
            p = db.get(StorybookProject, pid)
            p.status, p.limitation, p.retry_eligible, p.last_checked_at = "failed", f"{type(e).__name__}: {str(e)[:300]}", True, now()
            db.commit()
            return {"slug": p.slug, "error": f"{type(e).__name__}: {e}"}
