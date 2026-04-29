"""tender 앱 설정 — pydantic-settings."""

from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/learning"
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_expire_min: int = 30

    # Rate limit
    rate_limit_times: int = 30
    rate_limit_seconds: int = 60

    # Cache
    cache_ttl_seconds: int = 60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
