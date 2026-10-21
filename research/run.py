#!/usr/bin/env python3
"""DSKB pipeline entry point.

  python run.py extract [--only S01,S04] [--refresh] [--workers 6]
  python run.py build            # normalize → categorize → dedupe → validate → analyze → export
  python run.py all

Extraction is checkpointed per source in data/stage/<SID>.json; re-running skips completed sources
unless --refresh or --only is given. HTTP responses are cached with ETag/Last-Modified revalidation.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
from pathlib import Path

# The engine now lives in the backend (single source of truth); this CLI keeps file-based outputs under research/.
os.environ.setdefault("DSKB_DATA_DIR", str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.scrapers.dskb.core import CONFIG, STAGE, now_iso  # noqa: E402
from app.scrapers.dskb.sources import SEEDS  # noqa: E402
from app.scrapers.dskb.adapters import directories, libraries, repos  # noqa: E402

ADAPTERS = {
    "surf": directories.run_surf, "adele": directories.run_adele, "dsrepo": directories.run_dsrepo,
    "storybook": directories.run_storybook, "dsdir": directories.run_dsdir, "dsguide": directories.run_dsguide,
    "dscom": directories.run_dscom, "dsone": directories.run_dsone,
    "awesome": repos.run_awesome, "style_dictionary": repos.run_style_dictionary, "dtcg": repos.run_dtcg,
    "checklist": repos.run_checklist,
    "shadcn": libraries.run_shadcn, "radix": libraries.run_radix, "baseui": libraries.run_baseui,
    "reactaria": libraries.run_reactaria, "mantine": libraries.run_mantine, "antd": libraries.run_antd,
}


def extract(only=None, workers=6):
    STAGE.mkdir(parents=True, exist_ok=True)
    todo = [s for s in SEEDS if (not only or s["source_id"] in only)]
    if not only and not CONFIG.refresh:
        todo = [s for s in todo if not (STAGE / f"{s['source_id']}.json").exists()]
    print(f"[extract] {len(todo)} source(s): {', '.join(s['source_id'] for s in todo)}", flush=True)

    def one(seed):
        t0 = time.time()
        try:
            res = ADAPTERS[seed["adapter"]](seed)
        except Exception as e:
            from dskb.adapters.common import new_coverage
            cov = new_coverage(seed)
            cov["crawl_status"] = "adapter_error"
            cov["errors"].append(f"{type(e).__name__}: {e}")
            cov["traceback"] = traceback.format_exc()[-3000:]
            res = {"records": [], "coverage": cov}
        res["coverage"]["duration_s"] = round(time.time() - t0, 1)
        res["coverage"]["completed_at"] = now_iso()
        (STAGE / f"{seed['source_id']}.json").write_text(json.dumps(res, ensure_ascii=False))
        return seed["source_id"], res

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, s) for s in todo]
        for f in as_completed(futs):
            sid, res = f.result()
            c = res["coverage"]
            print(f"  {sid} {c['crawl_status']:<28} records={len(res['records']):>6} pages={c['pages_ok']}/{c['pages_attempted']} "
                  f"errors={len(c['errors'])} {c['duration_s']}s", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["extract", "build", "all"])
    ap.add_argument("--only", default="")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    CONFIG.refresh = a.refresh
    only = {x.strip().upper() for x in a.only.split(",") if x.strip()}
    if a.phase in ("extract", "all"):
        extract(only or None, a.workers)
    if a.phase in ("build", "all"):
        from app.scrapers.dskb import pipeline
        pipeline.build()


if __name__ == "__main__":
    sys.exit(main())
