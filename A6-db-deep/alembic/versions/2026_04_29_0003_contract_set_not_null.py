"""Expand-Contract STEP 5 — _Contract_: email_lower 를 NOT NULL 로 _제약_

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-29

전제 (운영 시나리오):
    0002 배포 후 _충분한 시간_ 동안 dual-write + backfill + switch-read 가 끝났음.
    이제 새 컬럼이 _완전히 채워졌고_ 앱이 _신 컬럼만_ 읽음. 옛 칼럼 제거 가능.

NOT NULL 제약:
    `ALTER TABLE deep_users ALTER COLUMN email_lower SET NOT NULL`
    → Postgres 12+ 에서 _즉시_ 적용 (ACCESS EXCLUSIVE 락 _짧게_).
    → 12 미만은 _전체 행 검사_ 라 길어짐 → CHECK 제약을 _NOT VALID_ 로 만들고 VALIDATE 분리.

본 마이그레이션은 _학습용_ 으로 SET NOT NULL 만 보여줌. 옛 컬럼 drop 까지는 _하지 않음_
(테스트가 단순해지도록). 운영에선 다음 단계로 `op.drop_column("deep_users", "email")`.

CHECK NOT VALID 패턴 (Postgres 11 미만 또는 더 안전하게):
    1) ALTER TABLE deep_users ADD CONSTRAINT chk_email_lower_nn CHECK (email_lower IS NOT NULL) NOT VALID
    2) (기존 데이터 백필 확인)
    3) ALTER TABLE deep_users VALIDATE CONSTRAINT chk_email_lower_nn   ← 락 없이 검증
    4) (필요시) ALTER COLUMN ... SET NOT NULL + DROP CONSTRAINT
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL 이 _없는지_ 안전 가드 — 있으면 즉시 실패. 운영에서는 모니터링 + 알람.
    null_count_row = op.get_bind().execute(
        sa.text("SELECT count(*) FROM deep_users WHERE email_lower IS NULL")
    )
    null_count = null_count_row.scalar_one()
    if null_count and null_count > 0:
        raise RuntimeError(
            f"email_lower 에 NULL {null_count} 행 존재 — 0002 의 backfill 미완료. "
            "운영에선 monitoring/alerting 으로 잡고 backfill 재실행."
        )

    op.alter_column("deep_users", "email_lower", nullable=False)


def downgrade() -> None:
    op.alter_column("deep_users", "email_lower", nullable=True)
