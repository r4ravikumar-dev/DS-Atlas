# Design-Systems Knowledge Base — Index

_Generated 2026-10-21T09:34:46.604770+00:00 · schema 1.0.0_

## Files

| File | Contents |
|---|---|
| `sources.json` / `sources.csv` | Source register: 20 seeds + discovered sources, crawl status, robots, coverage, errors |
| `design_systems_master.jsonl` | Every normalized record (one JSON object per line) **plus** canonical system entities (`source_id: KB`) |
| `design_systems.json` / `.csv` | Canonical design-system registry (entity-resolved across sources, with per-field provenance and conflicts) |
| `components.jsonl` / `.csv` | One record per documented component; structured `subcomponents[].props`, `keyboard`, `accessibility_notes` |
| `design_tokens.jsonl` | Token records with source-native names/values, type, theme, alias, component |
| `patterns_guidelines.jsonl` | Patterns, specifications-as-guidance, checklist items, governance descriptions, AI-readiness signals |
| `retrieval_chunks.jsonl` | Semantically coherent chunks for RAG, each with parent record, source, section, version, entity IDs |
| `design_system_comparison.md` | Evidence-backed comparison (libraries, families, API patterns, directory coverage) |
| `research_report.md` | Methodology, findings, trade-offs, recommendations, limitations, references |
| `crawl_report.json` | Coverage and error report (from the crawl manifest) + export validation results |
| `review_queue.json` | Conflicts and possible duplicates for manual review |
| `design_systems.db` | SQLite: normalized tables + FTS5 full-text index over chunks |
| `design_systems_catalog.xlsx` | Spreadsheet views of the same data |

## Counts

| Record type | Count |
|---|---|
| component | 3038 |
| guideline | 1739 |
| token | 1708 |
| system | 783 |
| resource | 413 |
| specification | 203 |
| tool | 172 |
| pattern | 55 |
| repository | 6 |
| canonical systems | 510 |

## Taxonomy

| ID | Category | Records | Subcategories |
|---|---|---|---|
| C01 | Design-System Strategy | 55 | vision, alignment, scope, maturity, adoption, metrics, roi, team, ownership, decision-making, roadmap, prioritization |
| C02 | Foundations | 1114 | color, typography, spacing, layout, sizing, responsive, breakpoints, radius, borders, elevation, iconography, illustration, photography, motion, sound-haptics, density, z-index, surfaces, brand |
| C03 | Design Tokens | 1969 | primitive, semantic, component, brand, theme, naming, hierarchy, aliases, types, groups, validation, versioning, deprecation, formats, dtcg, outputs, sync, design-tool, ci, governance |
| C04 | Component Architecture | 0 | taxonomy, anatomy, composition, slots, props, variants, sizes, states, interaction, controlled, compound, primitive, styled, recipes, deprecation, migration |
| C05 | Component Catalog | 3261 |  |
| C06 | Patterns and Product Workflows | 43 | auth, onboarding, search, filtering, crud, multi-step, confirmation, bulk, dashboard, errors, loading, empty-states |
| C07 | Accessibility and Inclusive Design | 28 | wcag, keyboard, focus, screen-readers, semantics, names, contrast, motion, touch, cognitive, forms, localization, rtl, testing |
| C08 | Documentation and Governance | 187 | structure, usage, dos-donts, status, contribution, rfcs, ownership, review, release, versioning, changelog, migration, deprecation, support, feedback, adoption |
| C09 | Engineering and Tooling | 324 | frameworks, typescript, css, tailwind, headless, storybook, testing, build, publishing, monorepo, ci, codegen, figma, docs-generation, performance, ssr, i18n |
| C10 | Theming and Brand Systems | 58 | multi-brand, inheritance, semantic-color, switching, dark-mode, high-contrast, density, white-label, runtime |
| C11 | Cross-Platform Design Systems | 0 | web, ios, android, desktop, react-native, parity, portability |
| C12 | Research and Comparative Analysis | 882 | comparison, strengths, limitations, trade-offs, recommendations |
| C13 | AI-Ready Design-System Knowledge | 196 | machine-readable, metadata, retrieval, ai-context, mcp, llms-txt, provenance |

## Record format

Common fields (all records): `record_id` (stable: `<type-prefix>:<source>:<slug>`), `record_type`, `title`, `summary`, `primary_category`, `secondary_categories`, `tags`, `organization`, `design_system`, `source_id`, `source_url`, `canonical_url`, `repository_url`, `source_file_path`, `source_section`, `source_version` (npm version or commit SHA), `source_status` (official/community/third_party/derived), `extraction_method`, `evidence_excerpt`, `normalized_content` (type-specific), `frameworks`, `platforms`, `technologies`, `license`, `confidence`, `verification_status`, `last_verified_at`, `relationships[]`, `duplicate_group_id`, `content_hash`, `notes[]`.

Type-specific `normalized_content`:

- **component**: `component_name`, `library`, `family`, `documentation_url`, `markdown_url`, `detail_level` (`api` | `doc` | `index` | `editorial_highlight`), `component_kind`, `subcomponents[{name, props[{name,type,default,description,required,since_version}], data_attributes[], css_variables[]}]`, `props_count`, `keyboard[{keys,description,section}]`, `accessibility_notes[]`, `examples[]`, `styles_api[]`, `section_outline[]`.
- **token**: `token_name`, `token_path`, `token_type` (+ `type_inferred`), `raw_value`, `resolved_value`, `alias_of`, `semantic_role`, `theme`, `platform`, `component`, `description`, `source_format`.
- **system** (source record): `name`, `organization`, `documentation_url`, `repository_url`, `storybook_url`, `design_resource_url`, `source_attributes` (verbatim directory fields).
- **system** (canonical, `source_id: KB`): registry fields listed in §7.1 of the brief with `framework_evidence`, `sources`, `source_record_ids`, `conflicts`, `verification_basis`.
- **guideline**: `kind` (`checklist_item`, `foundation_doc_link`, `library_documentation_page`, `design_specification`, `governance_description`, `ai_readiness_signal`) + kind fields.
- **specification**: DTCG sections with `normative_keywords`, `example_types`; token-type records with `type_identifiers`.

## Relationships

`documented_by_system`, `foundation_of`, `part_of`, `listed_in`, `defined_in`, `token_of`, `canonical_entity` (source record → `dsys:*`), `aggregates` (entity → source records). `duplicate_group_id`: `dsys:*` for systems, `dcmp:*` for the same component reported by several sources, `dres:*` for resources sharing a destination URL.

## Conventions

- `null` = unknown; empty array = known-empty. Nothing is invented to fill a field.
- `verification_status`: `verified` = read from the official source; `partially_verified` = corroborated by ≥2 independent sources or partially checked; `unverified` = single third-party claim.
- Families are an added normalisation; `component_name` keeps the source-native name.

## Search guidance

```bash
# All dialog components with keyboard documentation
jq -c 'select(.normalized_content.family=="Dialog" and (.normalized_content.keyboard|length)>0) | {title, source_url}' components.jsonl
# Systems with public tokens and a Storybook
jq -c '.[] | select(.storybook_url and .token_architecture) | {name, storybook_url}' design_systems.json
# Full-text search
sqlite3 design_systems.db "SELECT parent_record_id, snippet(chunks_fts,1,'[',']','…',12) FROM chunks_fts WHERE chunks_fts MATCH 'combobox AND keyboard' LIMIT 10;"
# Semantic token naming examples
sqlite3 design_systems.db "SELECT design_system, token_path, raw_value FROM tokens WHERE token_path LIKE '%primary%' LIMIT 20;"
```

## Update procedure

```bash
cd research
.venv/bin/python run.py extract --refresh   # re-crawl (revalidates cached responses)
.venv/bin/python run.py extract --only S15  # one source
.venv/bin/python run.py build             # rebuild every export from stage files
```

Stage checkpoints live in `data/stage/<SID>.json`; the HTTP cache and `data/crawl_manifest.jsonl` make runs resumable and auditable. `content_hash` supports change detection between runs.
