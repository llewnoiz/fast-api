"""DB 설정.

`database_url` 두 가지 모양:
    asyncpg URL: postgresql+asyncpg://user:pass@host:port/db   (FastAPI 라우트용 — async)
    psycopg URL: postgresql+psycopg://user:pass@host:port/db   (Alembic 마이그레이션용 — sync)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    # 기본은 asyncpg — async 앱이 사용
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/learning"
    )
    # SQL 로그 — 학습용으로 유용 (운영에선 noisy 라 끔)
    sql_echo: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
