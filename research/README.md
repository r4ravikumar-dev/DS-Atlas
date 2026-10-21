# DSKB — Design Systems Knowledge Base pipeline

Crawl → Extract → Normalize → Categorize → Deduplicate → Validate → Analyze → Export, over the 20 seed sources in `dskb/sources.py`.

```bash
python3 -m venv .venv && .venv/bin/pip install requests beautifulsoup4 lxml openpyxl pyyaml
.venv/bin/python run.py all                 # full run (resumable; per-source checkpoints in data/stage/)
.venv/bin/python run.py extract --only S15  # re-extract one source (HTTP cache + ETag revalidation)
.venv/bin/python run.py build               # rebuild every export from stage files
```

Optional: `GITHUB_TOKEN` raises the GitHub API limit (never written to outputs).

| Path | Purpose |
|---|---|
| `dskb/core.py` | Config, polite fetcher (robots.txt, per-host delay, retries, cache), GitHub access, record schema, Markdown parsing |
| `dskb/adapters/directories.py` | S01–S05, S17, S18, S20 |
| `dskb/adapters/repos.py` | S06–S10, S19 |
| `dskb/adapters/libraries.py` | S11–S16 |
| `dskb/pipeline.py` | Normalization, taxonomy, entity resolution, validation |
| `dskb/reports.py` | Comparison, report, index, crawl report, JSONL/CSV/SQLite/XLSX exports, export validation |
| `data/crawl_manifest.jsonl` | Every request with source, parent, depth, outcome, status, content hash |
| `output/` | Deliverables — start with `knowledge_base_index.md` |
