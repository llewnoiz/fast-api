"""앱 설정 — pydantic-settings.

dependency_overrides 에서 _Settings_ 를 갈아끼우는 패턴이 핵심.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/learning")
    redis_url: str = Field(default="redis://localhost:6379")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
