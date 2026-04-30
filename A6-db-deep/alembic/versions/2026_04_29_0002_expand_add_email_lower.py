"""Expand-Contract STEP 1 — _Expand_: email_lower 컬럼 _추가_ + 백필 (기본값 제공)

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-29

학습 목표 — Zero-downtime 마이그레이션 5 단계 패턴:
    1) **Expand** (이 마이그레이션): 새 컬럼/인덱스/테이블 _추가만_. 구 코드는 영향 없음.
    2) **Dual-write**: 앱 배포 — 새 코드가 _구 + 신_ 양쪽에 쓰기.
    3) **Backfill**: 과거 데이터를 신 컬럼으로 채우기 (배치).
    4) **Switch read**: 앱 배포 — 신 컬럼만 읽도록.
    5) **Contract** (다음 마이그레이션 0003): 구 컬럼 _제거_.

NEVER: 한 번에 ALTER TABLE ADD COLUMN NOT NULL ... — 기본값 없으면 _전 테이블 락_ + 다운타임.

본 마이그레이션은:
    - email_lower 컬럼 추가 (nullable, 기본값 없음 — 락 최소화)
    - 인덱스 _CONCURRENTLY_ 생성 — Postgres 만의 _운영급_ 패턴
        * 단, Alembic 트랜잭션 안에선 CONCURRENTLY 불가 → autocommit_block 사용

비교:
    Spring Flyway / Liquibase:
        같은 패턴 적용 가능. CONCURRENTLY 같은 PG 특화는 _수동 SQL_.
    Rails strong_migrations gem:
        unsafe 자동 검출 + 가이드 — _학습할 만한 가치 있음_.

NOTE: 학습용 — 실제로 깨는 변경은 아니지만, 패턴 _뼈대_ 를 보여주려고 별도 컬럼/인덱스 추가.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Step 1: 컬럼 _추가_ (nullable — 기존 행은 그냥 NULL).
    # 빠름. 메타데이터 변경만, 행 재작성 없음 (Postgres 11+).
    op.add_column(
        "deep_users",
        sa.Column("email_lower", sa.String(length=100), nullable=True),
    )

    # ── Step 2: 인덱스를 _CONCURRENTLY_ 로 생성 — 테이블 락 없이.
    # Alembic 의 트랜잭션을 잠시 벗어나야 함 (CONCURRENTLY 는 트랜잭션 불가).
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_deep_users_email_lower_v2 "
                "ON deep_users (email_lower)"
            )
        )

    # ── Step 3: 기존 행 _백필_ (학습용으론 한 번에 UPDATE — 운영은 _배치_ 로 끊어서).
    # 운영급: WHERE id BETWEEN ... 로 1만행씩 + sleep + 진행률 로그.
    op.execute(sa.text("UPDATE deep_users SET email_lower = lower(email)"))


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS ix_deep_users_email_lower_v2"))
    op.drop_column("deep_users", "email_lower")
