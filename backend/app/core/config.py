"""Environment-driven settings. Secrets come from the environment / .env (never committed)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Design Systems Research Platform API"
    environment: str = Field("development", description="development | test | production")
    api_prefix: str = "/api/v1"

    database_url: str = Field(..., description="SQLAlchemy URL, e.g. postgresql+psycopg://user:pass@host:5432/dsrp")
    db_pool_size: int = 10
    db_statement_timeout_ms: int = 15000

    secret_key: str = Field(..., min_length=32, description="HMAC key for session tokens")
    session_ttl_minutes: int = 8 * 60
    cookie_secure: bool = False
    cookie_domain: str | None = None
    allow_anonymous_read: bool = False
    cors_origins: list[str] = []

    storage_dir: Path = BACKEND_DIR / "storage"
    export_ttl_hours: int = 24

    worker_concurrency: int = 4
    worker_poll_seconds: float = 2.0
    job_heartbeat_timeout_seconds: int = 300

    app_base_url: str = Field("http://localhost:3000", description="Public origin of the frontend, used to build invitation links")
    invitation_ttl_hours: int = 72
    invitation_max_ttl_hours: int = 24 * 14
    email_transport: str = Field("outbox", description="smtp | outbox (development only: writes messages to storage/outbox) | disabled")
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True

    github_token: SecretStr | None = Field(None, description="Optional GitHub token (read-only public metadata). Never logged or returned.")

    max_page_size: int = 100
    default_page_size: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
