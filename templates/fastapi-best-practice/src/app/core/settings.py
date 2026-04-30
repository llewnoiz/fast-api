"""앱 설정 — pydantic-settings.

`.env` 또는 환경 변수에서 `APP_` 접두어로 로드.
운영 권장:
    - `APP_JWT_SECRET` 은 _절대_ default 사용 X. KMS / Vault / SealedSecrets.
    - `APP_DATABASE_URL` 은 docker compose 환경에서 호스트명 _컨테이너_ 기준으로 override.
"""

from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )

    env: str = "dev"
    log_level: str = "INFO"

    # DB / Cache
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_expire_min: int = 30

    # Cache TTL (초)
    cache_ttl_seconds: int = 60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """싱글톤. 테스트에서 환경변수 변경 후 `get_settings.cache_clear()` 필수."""
    return Settings()
