"""A8 설정."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="A8_", extra="ignore")

    redis_url: str = Field(default="redis://localhost:6379/0")
    # pub/sub 사용 여부 — 단일 인스턴스 학습이면 False, 다중 인스턴스 시뮬레이션이면 True
    use_pubsub: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
