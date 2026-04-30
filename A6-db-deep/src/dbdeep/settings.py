"""A6 DB 심화 — 설정.

10 단계와 동일 패턴 (asyncpg async URL + psycopg sync URL alembic). 학습 DB 는 별도로
`learning_deep` 스키마 권장 — 10 의 데이터를 안 건드리도록.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DBDEEP_", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/learning"
    )
    sql_echo: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
