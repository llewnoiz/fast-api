"""A7 설정."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="A7_", extra="ignore")

    redis_url: str = Field(default="redis://localhost:6379/0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
