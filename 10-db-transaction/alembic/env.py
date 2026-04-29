"""Alembic 환경 설정.

Alembic 자체는 _sync_ 라 psycopg(sync) 드라이버 사용. 앱 런타임은 asyncpg(async).
URL 만 다르고 같은 Postgres 를 가리킴.

비교:
    Spring:    Flyway, Liquibase
    NestJS:    typeorm migration:generate / migration:run
    Kotlin:    Flyway 또는 Exposed migration (제한적)
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from dbapp.models import Base

# Alembic Config — alembic.ini 의 값들 + 우리 모델 metadata
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 환경변수 우선 (운영/CI)
db_url = os.getenv("ALEMBIC_DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# autogenerate 가 비교할 _목표 스키마_
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """SQL 만 출력 — 실제 DB 에 안 붙음. CI / 검토용."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """실제 DB 에 적용."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
