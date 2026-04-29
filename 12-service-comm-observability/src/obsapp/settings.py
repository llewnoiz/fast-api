"""앱 설정."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    service_name: str = "obs-demo"
    env: str = "dev"

    # OTel 설정 — 운영에선 컬렉터 / OTLP endpoint
    otel_enabled: bool = True
    otel_endpoint: str = ""   # 비어있으면 콘솔로만 출력 (학습용)

    # 외부 호출 정책
    http_timeout_s: float = Field(default=2.0, gt=0)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    breaker_threshold: int = Field(default=3, ge=1, le=20)
    breaker_recovery_s: float = Field(default=5.0, gt=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
