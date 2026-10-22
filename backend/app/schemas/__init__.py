"""Purpose-designed API response/request models (decoupled from table shapes)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

T = TypeVar("T")

VerificationStatus = Literal["verified", "partially_verified", "unverified"]
JobStatus = Literal["queued", "running", "succeeded", "partially_succeeded", "failed", "cancelled"]
Role = Literal["admin", "researcher", "viewer"]


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageMeta(Model):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    facets: dict[str, int | str] | None = Field(None, description="Per-type hit counts (search only); `_match_mode: any` when the any-term fallback was used")


class Page(Model, Generic[T]):
    data: list[T]
    meta: PageMeta


class Item(Model, Generic[T]):
    data: T


class ErrorDetail(Model):
    field: str | None = None
    reason: str


class ErrorBody(Model):
    code: str
    message: str
    details: list[ErrorDetail] = []
    request_id: str | None = None


class ErrorResponse(Model):
    error: ErrorBody


# ───────────────────────────── auth / users ─────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=500)


class UserOut(Model):
    id: uuid.UUID
    email: str
    name: str
    role: Role
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class SessionOut(Model):
    user: UserOut
    csrf_token: str
    expires_in_seconds: int


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=500)
    new_password: str = Field(min_length=12, max_length=500)


# ───────────────────────────── sources ─────────────────────────────
class SourceOut(Model):
    id: int
    key: str
    name: str
    url: str
    domain: str
    source_type: str
    adapter: str
    origin: str
    status: str
    is_paused: bool
    http_status: int | None
    pages_attempted: int
    pages_ok: int
    records_count: int
    error_count: int
    last_attempted_at: datetime | None
    last_success_at: datetime | None


class SourceDetail(SourceOut):
    canonical_url: str
    resolved_url: str | None
    page_title: str | None
    crawl_limits: dict[str, Any]
    robots: dict[str, Any]
    coverage: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    url: HttpUrl
    source_type: Literal["directory", "documentation", "component_library", "resource_guide", "publication", "other"] = "documentation"
    max_pages: int = Field(30, ge=1, le=500)
    max_depth: int = Field(2, ge=0, le=5)


class SourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=300)
    is_paused: bool | None = None
    crawl_limits: dict[str, int] | None = None

    @field_validator("crawl_limits")
    @classmethod
    def _limits(cls, v):
        if v is None:
            return v
        allowed = {"max_pages": (1, 2000), "max_depth": (0, 5), "per_host_delay_ms": (500, 60000)}
        for k, val in v.items():
            if k not in allowed:
                raise ValueError(f"unsupported limit '{k}'")
            lo, hi = allowed[k]
            if not lo <= int(val) <= hi:
                raise ValueError(f"{k} must be between {lo} and {hi}")
        return v


class CoverageOut(Model):
    source_id: int
    key: str
    status: str
    pages_attempted: int
    pages_ok: int
    records_by_type: dict[str, int]
    urls_by_outcome: dict[str, int]
    limitations: list[str]
    errors: list[str]
    version_context: dict[str, Any]
    last_success_at: datetime | None


class DiscoveredUrlOut(Model):
    id: int
    url: str
    parent_url: str | None
    depth: int
    outcome: str
    http_status: int | None
    content_type: str | None
    fetch_count: int
    updated_at: datetime
    raw_document_id: int | None


# ───────────────────────────── jobs ─────────────────────────────
class JobOut(Model):
    id: uuid.UUID
    kind: str
    status: JobStatus
    phase: str | None
    source_id: int | None
    source_key: str | None = None
    source_name: str | None = None
    params: dict[str, Any]
    attempts: int
    urls_discovered: int
    urls_processed: int
    records_extracted: int
    error_count: int
    error: str | None
    cancel_requested: bool
    retry_of: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: dict[str, Any] = {}


class JobEventOut(Model):
    id: int
    ts: datetime
    level: str
    phase: str | None
    message: str
    data: dict[str, Any]


class CrawlRequest(BaseModel):
    source_ids: list[int] | None = Field(None, description="Omit to crawl all active sources")
    rebuild: bool = Field(True, description="Queue a knowledge-base build after the crawl jobs")


class JobAccepted(Model):
    job_ids: list[uuid.UUID]


# ───────────────────────────── knowledge ─────────────────────────────
class EvidenceOut(Model):
    id: int
    url: str
    excerpt: str | None
    source_file_path: str | None
    source_section: str | None
    source_version: str | None
    captured_at: datetime
    raw_document_id: int | None


ResourceType = Literal["official_website", "official_documentation", "github_repository", "figma_file", "storybook", "additional_resource"]


class ResourceLink(Model):
    """Primary link per resource type (as shown on catalog cards)."""
    type: ResourceType
    url: str
    verified: bool


class ResourceOut(Model):
    id: int
    system_id: int | None
    resource_type: ResourceType
    url: str
    label: str | None
    origin: str
    source_keys: list[str]
    verification_status: Literal["verified", "unverified", "invalid"]
    verification_method: str | None
    evidence_url: str | None
    evidence_note: str | None
    http_status: int | None
    access_note: str | None
    is_primary: bool
    last_checked_at: datetime | None
    updated_at: datetime


def _http_url(v: str) -> str:
    v = (v or "").strip()
    if not v.startswith(("https://", "http://")) or len(v) > 2000 or " " in v:
        raise ValueError("must be an absolute http(s) URL")
    return v


class ResourceCreate(BaseModel):
    resource_type: ResourceType
    url: str
    label: str | None = Field(None, max_length=300)
    verification_status: Literal["verified", "unverified"] = "unverified"
    evidence_note: str | None = Field(None, max_length=2000)
    _v = field_validator("url")(classmethod(lambda cls, v: _http_url(v)))


class ResourceUpdate(BaseModel):
    url: str | None = None
    label: str | None = Field(None, max_length=300)
    verification_status: Literal["verified", "unverified", "invalid"] | None = None
    evidence_note: str | None = Field(None, max_length=2000)
    is_primary: bool | None = None
    _v = field_validator("url")(classmethod(lambda cls, v: v if v is None else _http_url(v)))


class SystemOut(Model):
    id: int
    key: str
    name: str
    organization: str | None
    description: str | None
    documentation_url: str | None
    repository_url: str | None
    storybook_url: str | None
    official_docs_url: str | None = None
    related_urls: list[str] = []
    verification_coverage: dict[str, Any] = {}
    frameworks: list[str]
    platforms: list[str]
    styling_strategy: str | None
    token_architecture: str | None
    accessibility_documentation: str | None
    source_count: int
    source_keys: list[str]
    verification_status: VerificationStatus
    component_count: int
    token_count: int
    deprecated: bool
    last_verified_at: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    content_updated_at: datetime | None = None
    links: list[ResourceLink] = []
    resource_count: int = 0


class SystemDetail(SystemOut):
    design_resource_url: str | None
    governance: str | None
    ai_readiness: float | None
    verification_basis: str | None
    conflicts: dict[str, Any]
    aliases: list[str]
    attributes: dict[str, Any]
    resources: list[ResourceOut] = []
    merged_aliases: list[dict[str, Any]] = []
    requested_alias: dict[str, Any] | None = None
    storybook_projects: list[dict[str, Any]] = []
    story_count: int = 0
    variant_count: int = 0
    guideline_count: int = 0


class SystemUpdate(BaseModel):
    """Administrator edits of descriptive fields. Stored as audited curation, so they survive every rebuild."""
    name: str | None = Field(None, min_length=1, max_length=300)
    organization: str | None = Field(None, max_length=300)
    description: str | None = Field(None, max_length=5000)
    frameworks: list[str] | None = Field(None, max_length=30)
    platforms: list[str] | None = Field(None, max_length=30)
    styling_strategy: str | None = Field(None, max_length=200)


class IntakeCheck(BaseModel):
    url: str
    name: str | None = Field(None, max_length=300)
    _v = field_validator("url")(classmethod(lambda cls, v: _http_url(v)))


class IntakeCandidate(Model):
    system_id: int
    name: str
    organization: str | None
    match: str
    detail: str


class IntakeCheckOut(Model):
    url: str
    canonical_url: str
    suggested_type: ResourceType
    predicted_key: str | None
    candidates: list[IntakeCandidate]


class IntakeNewSystem(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    organization: str | None = Field(None, max_length=300)


class IntakeRequest(BaseModel):
    """Attach a URL to an existing system (system_id) or create a separate system (new_system).
    Creating a new system while likely duplicates exist requires separate_from = the candidate ids the administrator rejected."""
    url: str
    resource_type: ResourceType
    system_id: int | None = None
    new_system: IntakeNewSystem | None = None
    separate_from: list[int] = []
    verified: bool = False
    crawl: bool = True
    _v = field_validator("url")(classmethod(lambda cls, v: _http_url(v)))


class IntakeOut(Model):
    system_key: str
    system_id: int | None
    resource: ResourceOut | None
    source_id: int | None
    job_ids: list[uuid.UUID]


class PropOut(Model):
    subcomponent: str | None
    name: str
    type: str | None
    default_value: str | None
    description: str | None
    required: str | None


class ComponentOut(Model):
    id: int
    name: str
    family: str | None
    library: str | None
    system_id: int | None
    source_key: str
    detail_level: str | None
    kind: str | None
    description: str | None
    documentation_url: str | None
    props_count: int
    keyboard_count: int
    a11y_count: int
    frameworks: list[str]
    verification_status: VerificationStatus
    source_version: str | None


class ComponentDetail(ComponentOut):
    record_key: str
    source_url: str
    subcomponents: list[dict[str, Any]]
    props: list[PropOut]
    keyboard: list[dict[str, Any]]
    accessibility_notes: list[dict[str, Any]]
    examples: list[str]
    variants: dict[str, Any] | None
    data_attributes: list[dict[str, Any]]
    css_variables: list[dict[str, Any]]
    anatomy: str | None
    section_outline: list[str]
    notes: list[str]
    interpretation_note: str = "Fields are extracted verbatim from the cited documentation; `family` is a platform normalisation, not a source statement."


class TokenOut(Model):
    id: int
    name: str
    path: str
    group: str | None
    type: str | None
    type_inferred: bool
    raw_value: str | None
    resolved_value: str | None
    alias_of: str | None
    theme: str | None
    platform: str | None
    component: str | None
    description: str | None
    source_format: str | None
    design_system_name: str | None
    system_id: int | None
    source_key: str
    verification_status: VerificationStatus
    source_version: str | None


class GuidelineOut(Model):
    id: int
    record_type: str
    kind: str | None
    title: str
    category: str
    category_name: str
    summary: str | None
    section: str | None
    priority: str | None
    design_system_name: str | None
    source_key: str
    confidence: str
    verification_status: VerificationStatus
    review_status: str


class GuidelineDetail(GuidelineOut):
    record_key: str
    source_url: str
    content: dict[str, Any]
    evidence: list[EvidenceOut]


class SearchHit(Model):
    type: str
    id: str
    title: str
    subtitle: str | None
    snippet: str | None
    url: str
    source_key: str | None
    category: str | None
    rank: float


class FacetCount(Model):
    value: str
    count: int


class DashboardSummary(Model):
    sources_total: int
    sources_inspected: int
    sources_failed: int
    sources_never_crawled: int
    urls_discovered: int
    pages_processed: int
    design_systems: int
    systems_multi_source: int
    components: int
    components_with_api: int
    tokens: int
    guidelines: int
    patterns: int
    storybook_projects: int = 0
    storybook_stories: int = 0
    storybook_variants: int = 0
    attribute_evidence: int = 0
    review_open: int
    source_references: int = 0
    systems_verified: int = 0
    systems_partially_verified: int = 0
    systems_missing_official_link: int = 0
    resources: int = 0
    resources_verified: int = 0
    systems_with_figma: int = 0
    systems_with_github: int = 0
    extraction_errors: int = 0
    stale_records: int
    jobs_running: int
    last_crawl_at: datetime | None
    quality: dict[str, Any]


class ComparisonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["systems", "components"]
    item_ids: list[int] = Field(min_length=2, max_length=6)
    dimensions: list[str] = []


class ComparisonUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    item_ids: list[int] | None = Field(None, min_length=2, max_length=6)
    dimensions: list[str] | None = None


class ComparisonOut(Model):
    id: uuid.UUID
    name: str
    kind: str
    item_ids: list[int]
    dimensions: list[str]
    status: str
    result: dict[str, Any]
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReportOut(Model):
    id: uuid.UUID
    kind: str
    title: str
    created_at: datetime
    job_id: uuid.UUID | None


class ReportDetail(ReportOut):
    content_md: str
    data: dict[str, Any]


class ExportCreate(BaseModel):
    format: Literal["jsonl", "json", "csv", "markdown", "xlsx", "bundle"]
    resource: Literal["all", "systems", "components", "tokens", "guidelines", "sources"] = "all"


class ExportJobOut(Model):
    id: uuid.UUID
    status: JobStatus
    phase: str | None
    params: dict[str, Any]
    result: dict[str, Any]
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class DownloadLink(Model):
    url: str
    expires_at: datetime


class ReviewItemOut(Model):
    id: int
    key: str
    kind: str
    member_count: int
    review_status: str
    resolution: str | None = None
    decision_id: int | None = None
    details: dict[str, Any]
    resolution_note: str | None
    updated_at: datetime


class ReviewResolve(BaseModel):
    review_status: Literal["resolved", "dismissed", "open"]
    resolution_note: str | None = Field(None, max_length=2000)


class DuplicateDecision(BaseModel):
    """Administrator decision on a possible-duplicate item: merge every listed system into canonical_key, or keep them distinct."""
    decision: Literal["merge", "distinct"]
    canonical_key: str | None = Field(None, max_length=300)
    note: str = Field(min_length=3, max_length=2000, description="Why (evidence the administrator relied on)")


class AuditEventOut(Model):
    id: int
    ts: datetime
    user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    details: dict[str, Any]
    request_id: str | None


class ConfigOut(Model):
    approved_domains: list[str]
    crawl_defaults: dict[str, Any]
    retention: dict[str, Any]
    export_policy: dict[str, Any]
    schedule: dict[str, Any]
    data_quality_rules: dict[str, Any]


class ConfigUpdate(BaseModel):
    approved_domains: list[str] | None = None
    crawl_defaults: dict[str, Any] | None = None
    retention: dict[str, Any] | None = None
    export_policy: dict[str, Any] | None = None
    schedule: dict[str, Any] | None = None
    data_quality_rules: dict[str, Any] | None = None

    @field_validator("approved_domains")
    @classmethod
    def _domains(cls, v):
        import re
        if v is None:
            return v
        for d in v:
            if not re.fullmatch(r"(?=.{1,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,63}", d.lower()):
                raise ValueError(f"invalid domain '{d}'")
        return sorted({d.lower() for d in v})


# ───────────────────────────── invitations & access ─────────────────────────────
class AttributeEvidenceOut(Model):
    id: int
    system_id: int | None
    system_key: str
    attribute_path: str
    value: Any
    source_url: str
    source_section: str | None
    source_version: str | None
    excerpt: str | None
    verification_status: str
    method: str
    checked_at: datetime


class ComponentStorybookOut(Model):
    stories: list[dict[str, Any]]
    variants: list[dict[str, Any]]

