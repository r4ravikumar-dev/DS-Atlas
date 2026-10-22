"""Environment-driven settings. Secrets come from the environment / .env (never committed)."""
from __future__ import annotations

import os

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Design Systems Research Platform API"
    environment: str = Field("development", description="development | test | production")
    api_prefix: str = "/api/v1"

    database_url: str = Field(..., description="SQLAlchemy URL, e.g. postgresql+psycopg://user:pass@host:5432/dsrp")
    db_pool_mode: Literal["auto", "direct", "transaction"] = Field(
        "auto", description="transaction = a transaction-mode pooler such as Supabase Supavisor on port 6543 (no client pool, no prepared "
                            "statements, no session SETs). auto picks transaction for port 6543.")
    db_pool_size: int = 10
    db_statement_timeout_ms: int = 15000

    secret_key: str = Field(..., min_length=32, description="HMAC key for session tokens")
    session_ttl_minutes: int = 8 * 60
    cookie_secure: bool = False
    cookie_domain: str | None = None
    cors_origins: list[str] = []

    # On Vercel Functions only /tmp is writable (and ephemeral); elsewhere storage lives next to the code. Override with STORAGE_DIR.
    storage_dir: Path = Field(default_factory=lambda: Path("/tmp/dsrp-storage") if os.environ.get("VERCEL") else BACKEND_DIR / "storage")
    export_ttl_hours: int = 24
    # Object storage for raw snapshots and exports. "local" = STORAGE_DIR; "supabase" = a private Supabase Storage bucket, shared by the
    # API functions and the worker. The service-role key is server-side only (never sent to the browser or logged).
    storage_backend: Literal["local", "supabase"] = "local"
    supabase_url: str | None = Field(None, description="https://<project-ref>.supabase.co")
    supabase_service_role_key: SecretStr | None = None
    supabase_storage_bucket: str = "dsrp-private"
    signed_url_ttl_seconds: int = 60

    worker_concurrency: int = 4
    worker_poll_seconds: float = 2.0
    job_heartbeat_timeout_seconds: int = 300

    github_token: SecretStr | None = Field(None, description="Optional GitHub token (read-only public metadata). Never logged or returned.")

    max_page_size: int = 100
    default_page_size: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
