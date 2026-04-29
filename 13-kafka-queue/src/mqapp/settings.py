"""13 단계 설정."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    # Kafka — 컨테이너 내부면 "kafka:29092", 호스트면 "localhost:9092"
    kafka_bootstrap: str = "localhost:9092"
    kafka_topic: str = "demo.events"
    kafka_consumer_group: str = "demo-consumers"

    # arq (Redis 기반)
    redis_url: str = "redis://localhost:6379"

    # outbox 의 underlying DB
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/learning"

    # outbox relay polling 주기
    outbox_poll_interval_s: float = Field(default=1.0, gt=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
