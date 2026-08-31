"""Environment-backed runtime configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RECONCILEFLOW_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    repository_backend: Literal["memory", "sqlalchemy"] = "memory"
    database_url: str = "sqlite+pysqlite:///./reconcileflow.db"
    redis_url: str = "redis://localhost:6379/0"
    async_enabled: bool = False
    async_row_threshold: int = Field(default=10_000, ge=1)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    max_upload_rows: int = Field(default=100_000, ge=1)
    cors_origins: str = "http://localhost:5173"
    api_host: str = "127.0.0.1"
    log_level: str = "INFO"
    otel_enabled: bool = False

    @property
    def allowed_origins(self) -> tuple[str, ...]:
        return tuple(item.strip() for item in self.cors_origins.split(",") if item.strip())
