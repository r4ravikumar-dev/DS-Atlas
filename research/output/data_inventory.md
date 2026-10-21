# Design Systems Research Platform — Comprehensive Data Inventory

**Generated:** `2026-10-21T11:58:24.905925+00:00`  
**Authoritative Store:** PostgreSQL Database (`dsrp`) + Content-Addressed Object Store (`storage/`)  
**Exports Synchronization:** `research/output/`  

## 1. Summary of Storage Locations & Collections

| Record Category | Storage Location | Total Records | Valid Records | Unverified / Open | Records w/ Evidence | API Exposed | Frontend Route |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Source** | `PostgreSQL: sources table` | 32 | 31 | 0 | 31 | ✅ | ✅ |
| **DiscoveredUrl** | `PostgreSQL: discovered_urls table` | 1,541 | 1,512 | 29 | 1,600 | ✅ | ✅ |
| **DesignSystem** | `PostgreSQL: design_systems table` | 477 | 477 | 342 | 477 | ✅ | ✅ |
| **AttributeEvidence** | `PostgreSQL: attribute_evidence table` | 312 | 312 | 0 | 312 | ✅ | ⚠️ Missing |
| **Component** | `PostgreSQL: components table` | 3,385 | 3,385 | 2,589 | 3,385 | ✅ | ✅ |
| **ComponentProp** | `PostgreSQL: component_props table` | 22,066 | 22,066 | 0 | 22,066 | ✅ | ✅ |
| **StorybookProject** | `PostgreSQL: storybook_projects table` | 103 | 0 | 103 | 103 | ✅ | ⚠️ Missing |
| **StorybookStory** | `PostgreSQL: storybook_stories table` | 17,600 | 17,600 | 0 | 17,600 | ✅ | ⚠️ Missing |
| **StorybookVariant** | `PostgreSQL: storybook_variants table` | 12,150 | 12,150 | 0 | 12,150 | ✅ | ⚠️ Missing |
| **DesignToken** | `PostgreSQL: design_tokens table` | 1,708 | 1,708 | 290 | 1,708 | ✅ | ✅ |
| **TokenReference** | `PostgreSQL: token_references table` | 287 | 287 | 0 | 287 | ✅ | ✅ |
| **Pattern** | `PostgreSQL: guidelines table (record_type = pattern)` | 55 | 55 | 0 | 55 | ✅ | ✅ |
| **Guideline** | `PostgreSQL: guidelines table (record_type in guideline, specification)` | 1,942 | 1,942 | 0 | 1,942 | ✅ | ✅ |
| **Repository** | `PostgreSQL: records table (record_type = repository)` | 6 | 6 | 0 | 6 | ✅ | ✅ |
| **Evidence** | `PostgreSQL: evidence table` | 8,690 | 8,690 | 0 | 8,690 | ✅ | ✅ |
| **CrawlJob** | `PostgreSQL: jobs table` | 45 | 44 | 1 | 45 | ✅ | ✅ |
| **DuplicateGroup** | `PostgreSQL: duplicate_groups table` | 130 | 126 | 4 | 130 | ✅ | ✅ |
| **ReportAndExport** | `PostgreSQL: reports, comparisons tables` | 41 | 41 | 0 | 40 | ✅ | ✅ |

## 2. Category Details & Provenance Analysis

### Source
- **Primary Storage:** `PostgreSQL: sources table; research/output/sources.json, sources.csv`
- **Total Records:** 32
- **Valid Records:** 31
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 31 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 32 sources: 20 seeds + 12 registered official documentation sources (O01-O12).

### DiscoveredUrl
- **Primary Storage:** `PostgreSQL: discovered_urls table; raw_documents table`
- **Total Records:** 1,541
- **Valid Records:** 1,512
- **Unverified / Open Records:** 29
- **Orphaned Records:** 0
- **Evidence Linkage:** 1,600 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 1,541 discovered URLs across sources; 1,600 content-addressed raw snapshots stored in raw_documents.

### DesignSystem
- **Primary Storage:** `PostgreSQL: design_systems table; research/output/design_systems.json, design_systems.csv`
- **Total Records:** 477
- **Valid Records:** 477
- **Unverified / Open Records:** 342
- **Orphaned Records:** 0
- **Evidence Linkage:** 477 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 477 canonical systems. 135 partially verified from multi-source cross-referencing and official docs; 342 single-source unverified directory entries.

### AttributeEvidence
- **Primary Storage:** `PostgreSQL: attribute_evidence table; research/output/design_system_attribute_evidence.jsonl`
- **Total Records:** 312
- **Valid Records:** 312
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 312 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Missing from Navigation/Views
- **Notes:** 312 verified attribute evidence records extracted from O01-O12 official docs crawls. Missing dedicated frontend view.

### Component
- **Primary Storage:** `PostgreSQL: components table; research/output/components.jsonl, components.csv`
- **Total Records:** 3,385
- **Valid Records:** 3,385
- **Unverified / Open Records:** 2,589
- **Orphaned Records:** 0
- **Evidence Linkage:** 3,385 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 3,385 component records across 477 design systems. 1,029 with structured props/APIs.

### ComponentProp
- **Primary Storage:** `PostgreSQL: component_props table`
- **Total Records:** 22,066
- **Valid Records:** 22,066
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 22,066 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 22,066 structured component properties across 1,029 component interfaces.

### StorybookProject
- **Primary Storage:** `PostgreSQL: storybook_projects table; research/output/storybook_project_registry.json`
- **Total Records:** 103
- **Valid Records:** 0
- **Unverified / Open Records:** 103
- **Orphaned Records:** 0
- **Evidence Linkage:** 103 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Missing from Navigation/Views
- **Notes:** 103 showcase projects inspected: 40 public index extracted, 63 classified unindexed/blocked.

### StorybookStory
- **Primary Storage:** `PostgreSQL: storybook_stories table; research/output/storybook_stories.jsonl`
- **Total Records:** 17,600
- **Valid Records:** 17,600
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 17,600 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Missing from Navigation/Views
- **Notes:** 17,600 story entries (14,491 stories, 2,646 autodocs, 463 docs). 728 linked to canonical components.

### StorybookVariant
- **Primary Storage:** `PostgreSQL: storybook_variants table; research/output/storybook_component_variants.jsonl`
- **Total Records:** 12,150
- **Valid Records:** 12,150
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 12,150 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Missing from Navigation/Views
- **Notes:** 12,150 component variant combinations extracted via story_args, arg_types, and story naming.

### DesignToken
- **Primary Storage:** `PostgreSQL: design_tokens table`
- **Total Records:** 1,708
- **Valid Records:** 1,708
- **Unverified / Open Records:** 290
- **Orphaned Records:** 0
- **Evidence Linkage:** 1,708 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 1,708 design tokens extracted from Figma tokens, W3C DTCG specs, CSS custom properties, and SCSS variables.

### TokenReference
- **Primary Storage:** `PostgreSQL: token_references table`
- **Total Records:** 287
- **Valid Records:** 287
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 287 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 287 alias relationships linking composite semantic tokens to core base scales.

### Pattern
- **Primary Storage:** `PostgreSQL: guidelines table (record_type = pattern)`
- **Total Records:** 55
- **Valid Records:** 55
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 55 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 55 interaction and UX design patterns.

### Guideline
- **Primary Storage:** `PostgreSQL: guidelines table (record_type in guideline, specification)`
- **Total Records:** 1,942
- **Valid Records:** 1,942
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 1,942 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 1,942 accessibility, content, layout, color, and technical specifications.

### Repository
- **Primary Storage:** `PostgreSQL: records table (record_type = repository); design_systems.repository_url`
- **Total Records:** 6
- **Valid Records:** 6
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 6 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 6 repository records; 221 canonical design systems have verified repository URLs.

### Evidence
- **Primary Storage:** `PostgreSQL: evidence table`
- **Total Records:** 8,690
- **Valid Records:** 8,690
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 8,690 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 8,690 citation records tying extracted entities to source URLs, DOM excerpts, and snapshots.

### CrawlJob
- **Primary Storage:** `PostgreSQL: jobs table`
- **Total Records:** 45
- **Valid Records:** 44
- **Unverified / Open Records:** 1
- **Orphaned Records:** 0
- **Evidence Linkage:** 45 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 45 total jobs (1 failed, 0 queued, 0 running).

### DuplicateGroup
- **Primary Storage:** `PostgreSQL: duplicate_groups table; review_decisions, identity_links, entity_curation tables`
- **Total Records:** 130
- **Valid Records:** 126
- **Unverified / Open Records:** 4
- **Orphaned Records:** 0
- **Evidence Linkage:** 130 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 130 review groups total: 126 resolved during initial queue resolution; 4 newly detected open component duplicates from official crawls.

### ReportAndExport
- **Primary Storage:** `PostgreSQL: reports, comparisons tables; research/output/ master exports`
- **Total Records:** 41
- **Valid Records:** 41
- **Unverified / Open Records:** 0
- **Orphaned Records:** 0
- **Evidence Linkage:** 40 records linked to raw snapshots or source URLs
- **API Exposure Status:** Exposed
- **Frontend Representation Status:** Represented
- **Notes:** 40 research reports, 1 comparison, and synchronized CSV/JSON/JSONL/Markdown master exports.
