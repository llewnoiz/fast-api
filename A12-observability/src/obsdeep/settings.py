"""A12 설정."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="A12_", extra="ignore")

    service_name: str = Field(default="obsdeep")
    environment: str = Field(default="dev")
    sentry_dsn: str | None = Field(default=None)  # 비어있으면 _Sentry 비활성_ — 학습용
    sentry_traces_sample_rate: float = Field(default=0.0)  # 학습용 0% — 운영은 0.01~0.1
    sentry_profiles_sample_rate: float = Field(default=0.0)
    log_level: str = Field(default="INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
