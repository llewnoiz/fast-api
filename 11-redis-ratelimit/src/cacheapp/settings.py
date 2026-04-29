"""Redis 설정."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    redis_url: str = Field(default="redis://localhost:6379")

    # 키 네이밍 prefix — 멀티테넌트 / 환경 분리에 유용
    # 예: "myapp:dev:" 으로 두면 prod 와 충돌 방지
    cache_prefix: str = "app:"

    cache_default_ttl: int = Field(default=60, ge=1, le=86_400)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
