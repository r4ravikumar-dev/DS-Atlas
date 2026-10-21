"""Relational schema. Source-specific variable fields live in JSONB; identity, relationships,
lookup and filter fields are first-class columns with constraints and indexes."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (BigInteger, Boolean, Computed, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ───────────────────────────── identity & access ─────────────────────────────
class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")  # admin | researcher | viewer
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")  # bump to invalidate all sessions
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppSetting(TimestampMixin, Base):
    """Operational configuration editable by administrators (no secrets stored here)."""
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(200))
    details: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    request_id: Mapped[str | None] = mapped_column(String(64))


# ───────────────────────────── sources & crawling ─────────────────────────────
class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # S01…S20, U001… for user-added
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    adapter: Mapped[str] = mapped_column(String(50), nullable=False)
    origin: Mapped[str] = mapped_column(String(20), nullable=False, default="seed")  # seed | user | official
    system_key: Mapped[str | None] = mapped_column(String(300), index=True)  # canonical system an official-docs source verifies
    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    crawl_limits: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    # latest crawl outcome (denormalized for list views; history lives in jobs)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="never_crawled", index=True)
    http_status: Mapped[int | None] = mapped_column(Integer)
    resolved_url: Mapped[str | None] = mapped_column(Text)
    page_title: Mapped[str | None] = mapped_column(Text)
    robots: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    coverage: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    pages_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_ok: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector = mapped_column(TSVECTOR, Computed("to_tsvector('simple', coalesce(name,'') || ' ' || coalesce(url,'') || ' ' || coalesce(source_type,''))", persisted=True))
    __table_args__ = (Index("ix_sources_search", "search_vector", postgresql_using="gin"),)


class Job(TimestampMixin, Base):
    """Durable background job (crawl | build | export | comparison). Claimed with FOR UPDATE SKIP LOCKED."""
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)
    phase: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    params: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    urls_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    urls_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retry_of: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(100))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source = relationship("Source")
    __table_args__ = (Index("ix_jobs_claim", "status", "run_after", "priority", "created_at"),)


class JobEvent(Base):
    __tablename__ = "job_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False, default="info")
    phase: Mapped[str | None] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)


class RawDocument(Base):
    """Content-addressed snapshot metadata; bytes live in object storage (local FS adapter by default)."""
    __tablename__ = "raw_documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    first_url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiscoveredUrl(TimestampMixin, Base):
    __tablename__ = "discovered_urls"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    parent_url: Mapped[str | None] = mapped_column(Text)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    final_url: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(200))
    raw_document_id: Mapped[int | None] = mapped_column(ForeignKey("raw_documents.id", ondelete="SET NULL"))
    last_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    fetch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("source_id", "url", name="uq_discovered_source_url"),)


# ───────────────────────────── extracted knowledge ─────────────────────────────
class Record(TimestampMixin, Base):
    """Every extracted finding (system listing, component, token, guideline, pattern, resource, spec, tool, repository).
    `record_key` is the engine's deterministic ID, so re-crawls upsert instead of duplicating."""
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    record_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    primary_category: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    secondary_categories: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    organization: Mapped[str | None] = mapped_column(String(300), index=True)
    design_system_name: Mapped[str | None] = mapped_column(String(300), index=True)
    system_id: Mapped[int | None] = mapped_column(ForeignKey("design_systems.id", ondelete="SET NULL"), index=True)
    source_version: Mapped[str | None] = mapped_column(String(200))
    source_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    extraction_method: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    frameworks: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    technologies: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    license: Mapped[str | None] = mapped_column(String(100))
    content: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)  # normalized_content
    extra: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)  # remaining engine fields (notes, file path, …)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    duplicate_group_key: Mapped[str | None] = mapped_column(String(300), index=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    first_seen_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    last_seen_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector = mapped_column(TSVECTOR, Computed(
        "setweight(to_tsvector('english', coalesce(title,'')), 'A') || "
        "setweight(to_tsvector('english', coalesce(design_system_name,'') || ' ' || coalesce(organization,'')), 'B') || "
        "setweight(to_tsvector('english', coalesce(summary,'')), 'C')", persisted=True))
    source = relationship("Source")
    __table_args__ = (Index("ix_records_search", "search_vector", postgresql_using="gin"),
                      Index("ix_records_type_source", "record_type", "source_id"))


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    source_file_path: Mapped[str | None] = mapped_column(Text)
    source_section: Mapped[str | None] = mapped_column(Text)
    source_version: Mapped[str | None] = mapped_column(String(200))
    raw_document_id: Mapped[int | None] = mapped_column(ForeignKey("raw_documents.id", ondelete="SET NULL"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("record_id", "url", name="uq_evidence_record_url"),)


class DesignSystem(TimestampMixin, Base):
    """Canonical, entity-resolved design system (rebuilt from records by the build job)."""
    __tablename__ = "design_systems"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    organization: Mapped[str | None] = mapped_column(String(300), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    documentation_url: Mapped[str | None] = mapped_column(Text)
    repository_url: Mapped[str | None] = mapped_column(Text)
    storybook_url: Mapped[str | None] = mapped_column(Text)
    design_resource_url: Mapped[str | None] = mapped_column(Text)
    frameworks: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    platforms: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    styling_strategy: Mapped[str | None] = mapped_column(Text)
    token_architecture: Mapped[str | None] = mapped_column(Text)
    accessibility_documentation: Mapped[str | None] = mapped_column(Text)
    governance: Mapped[str | None] = mapped_column(Text)
    ai_readiness: Mapped[float | None] = mapped_column(Float)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    source_keys: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    verification_basis: Mapped[str | None] = mapped_column(Text)
    conflicts: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    aliases: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    attributes: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    component_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    official_docs_url: Mapped[str | None] = mapped_column(Text)
    related_urls: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    verification_coverage: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector = mapped_column(TSVECTOR, Computed(
        "setweight(to_tsvector('english', coalesce(name,'')), 'A') || setweight(to_tsvector('english', coalesce(organization,'')), 'A') || "
        "setweight(to_tsvector('english', coalesce(description,'')), 'C')", persisted=True))
    __table_args__ = (Index("ix_systems_search", "search_vector", postgresql_using="gin"),)


class Component(Base):
    __tablename__ = "components"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    family: Mapped[str | None] = mapped_column(String(100), index=True)
    library: Mapped[str | None] = mapped_column(String(300), index=True)
    system_id: Mapped[int | None] = mapped_column(ForeignKey("design_systems.id", ondelete="SET NULL"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    detail_level: Mapped[str | None] = mapped_column(String(30), index=True)
    kind: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    documentation_url: Mapped[str | None] = mapped_column(Text)
    props_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    keyboard_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    a11y_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frameworks: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(200))
    record = relationship("Record")
    __table_args__ = (Index("ix_components_lib_family", "library", "family"),)


class ComponentProp(Base):
    __tablename__ = "component_props"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), nullable=False, index=True)
    subcomponent: Mapped[str | None] = mapped_column(String(300))
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    type: Mapped[str | None] = mapped_column(Text)
    default_value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    required: Mapped[str | None] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DesignToken(Base):
    __tablename__ = "design_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    group: Mapped[str | None] = mapped_column(String(200), index=True)
    type: Mapped[str | None] = mapped_column(String(200), index=True)
    type_inferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_value: Mapped[str | None] = mapped_column(Text)
    resolved_value: Mapped[str | None] = mapped_column(Text)
    alias_of: Mapped[str | None] = mapped_column(String(500))
    theme: Mapped[str | None] = mapped_column(String(50), index=True)
    platform: Mapped[str | None] = mapped_column(String(50), index=True)
    component: Mapped[str | None] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source_format: Mapped[str | None] = mapped_column(String(200))
    design_system_name: Mapped[str | None] = mapped_column(String(300), index=True)
    system_id: Mapped[int | None] = mapped_column(ForeignKey("design_systems.id", ondelete="SET NULL"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(200))
    record = relationship("Record")


class TokenReference(Base):
    __tablename__ = "token_references"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey("design_tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    references_token_id: Mapped[int] = mapped_column(ForeignKey("design_tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("token_id", "references_token_id", name="uq_token_ref"),)


class Guideline(Base):
    """Guidelines, patterns and specification sections (record_type distinguishes them)."""
    __tablename__ = "guidelines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), unique=True, nullable=False)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    kind: Mapped[str | None] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    section: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(String(20))
    design_system_name: Mapped[str | None] = mapped_column(String(300), index=True)
    system_id: Mapped[int | None] = mapped_column(ForeignKey("design_systems.id", ondelete="SET NULL"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unreviewed")
    record = relationship("Record")


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    from_record_id: Mapped[int] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    to_record_id: Mapped[int | None] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), index=True)
    to_system_id: Mapped[int | None] = mapped_column(ForeignKey("design_systems.id", ondelete="CASCADE"), index=True)


class DuplicateGroup(TimestampMixin, Base):
    """Review queue: conflicts, possible duplicates, multi-source duplicates."""
    __tablename__ = "duplicate_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(400), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    details: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(String(40), index=True)  # resolved_existing_system | duplicate_confirmed | linked_resource | …
    decision_id: Mapped[int | None] = mapped_column(Integer)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


# ───────────────────────────── analysis artefacts ─────────────────────────────
class Comparison(TimestampMixin, Base):
    __tablename__ = "comparisons"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # systems | components
    item_ids: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    dimensions: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    result: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# ───────────────────────────── enrichment (review, verification, storybook, API usage) ─────────────────────────────
class ReviewDecision(Base):
    """Immutable log of review decisions (automated resolver or human) with supporting evidence."""
    __tablename__ = "review_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_key: Mapped[str] = mapped_column(String(400), nullable=False, index=True)
    item_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    canonical_key: Mapped[str | None] = mapped_column(String(300))
    related_keys: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    method: Mapped[str] = mapped_column(String(80), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    original_item: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    decided_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IdentityLink(Base):
    """Evidence-backed identity relations between canonical entities, applied by every build.
    same_as merges `from_key` into `to_key`; implementation_of / related_to link distinct entities; distinct_from records separation."""
    __tablename__ = "identity_links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_key: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    to_key: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(30), nullable=False)
    decision_id: Mapped[int | None] = mapped_column(ForeignKey("review_decisions.id", ondelete="SET NULL"))
    evidence: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("from_key", "to_key", "relation", name="uq_identity_link"),)


class EntityCuration(Base):
    """Evidence-backed field values for canonical entities (e.g. verified official docs URL), applied by every build."""
    __tablename__ = "entity_curation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_key: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(60), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    decision_id: Mapped[int | None] = mapped_column(ForeignKey("review_decisions.id", ondelete="SET NULL"))
    evidence: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("entity_key", "field", name="uq_entity_curation"),)


class AttributeEvidence(Base):
    """Field-level verification: one row per (system, attribute, source URL)."""
    __tablename__ = "attribute_evidence"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    evidence_key: Mapped[str] = mapped_column(String(400), unique=True, nullable=False)
    system_key: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    system_id: Mapped[int | None] = mapped_column(ForeignKey("design_systems.id", ondelete="SET NULL"), index=True)
    attribute_path: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_section: Mapped[str | None] = mapped_column(Text)
    source_version: Mapped[str | None] = mapped_column(String(200))
    excerpt: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StorybookProject(TimestampMixin, Base):
    __tablename__ = "storybook_projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(300))
    storybook_url: Mapped[str | None] = mapped_column(Text)
    resolved_url: Mapped[str | None] = mapped_column(Text)
    repository_url: Mapped[str | None] = mapped_column(Text)
    framework: Mapped[str | None] = mapped_column(String(100))
    storybook_version: Mapped[str | None] = mapped_column(String(50))
    system_key: Mapped[str | None] = mapped_column(String(300), index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    index_kind: Mapped[str | None] = mapped_column(String(30))
    stories_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stories_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    docs_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    variants_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_files_parsed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limitation: Mapped[str | None] = mapped_column(Text)
    retry_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    index_sha256: Mapped[str | None] = mapped_column(String(64))
    raw_index_document_id: Mapped[int | None] = mapped_column(ForeignKey("raw_documents.id", ondelete="SET NULL"))
    showcase_record_key: Mapped[str | None] = mapped_column(String(300))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StorybookStory(Base):
    __tablename__ = "storybook_stories"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    story_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("storybook_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_id: Mapped[str] = mapped_column(String(400), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # story | docs | autodocs | unknown
    title: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    export_name: Mapped[str | None] = mapped_column(String(300))
    component_name: Mapped[str | None] = mapped_column(String(300), index=True)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("components.id", ondelete="SET NULL"), index=True)
    resolution_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unresolved", index=True)
    tags: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    import_path: Mapped[str | None] = mapped_column(Text)
    story_url: Mapped[str] = mapped_column(Text, nullable=False)
    args: Mapped[Any] = mapped_column(JSONB, nullable=True)
    arg_types: Mapped[Any] = mapped_column(JSONB, nullable=True)
    source_file_url: Mapped[str | None] = mapped_column(Text)
    extraction_status: Mapped[str] = mapped_column(String(20), nullable=False, default="index_only")
    evidence: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StorybookVariant(Base):
    __tablename__ = "storybook_variants"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    variant_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    story_id: Mapped[int] = mapped_column(ForeignKey("storybook_stories.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("storybook_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("components.id", ondelete="SET NULL"), index=True)
    component_name: Mapped[str | None] = mapped_column(String(300))
    label: Mapped[str] = mapped_column(Text, nullable=False)
    props: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    method: Mapped[str] = mapped_column(String(40), nullable=False)  # story_args | arg_types_options | story_name_inference
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    evidence: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)


class ApiUsage(Base):
    """Per-request GitHub API usage/rate-limit telemetry (never stores credentials)."""
    __tablename__ = "api_usage"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    authenticated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rate_limit: Mapped[int | None] = mapped_column(Integer)
    rate_remaining: Mapped[int | None] = mapped_column(Integer)
    rate_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rate_resource: Mapped[str | None] = mapped_column(String(40))
    retry_after_s: Mapped[int | None] = mapped_column(Integer)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Invitation(Base):
    """Identity-bound, expiring, single-use access grant. Only an HMAC digest of the token is stored.
    kind=access creates a membership; kind=reset re-keys an existing account's password."""
    __tablename__ = "invitations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="access")
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    delivery_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending | sent | failed | not_configured
    delivery_error: Mapped[str | None] = mapped_column(Text)
    send_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    code_digest: Mapped[str | None] = mapped_column(String(64))
    code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    code_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    code_sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
