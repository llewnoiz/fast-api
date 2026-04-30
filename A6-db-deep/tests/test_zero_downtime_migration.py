"""Expand-Contract 마이그레이션 검증.

학습 의도: alembic upgrade head 가 _세 단계_ (0001 → 0002 → 0003) 모두 적용했고
   email_lower 가 NOT NULL 로 도달했는지 확인.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def test_email_lower_column_is_not_null(seeded_session: AsyncSession) -> None:
    """0003 까지 적용 — email_lower 가 NOT NULL 이어야."""
    is_nullable = (
        await seeded_session.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'deep_users' AND column_name = 'email_lower'"
            )
        )
    ).scalar_one()
    assert is_nullable == "NO"


async def test_email_lower_backfilled(seeded_session: AsyncSession) -> None:
    """0002 의 백필이 _시드 데이터에도_ 적용됐는지.

    주의: 시드는 _마이그레이션 후_ 에 들어가므로, ORM 이 채우지 않은 채 기본값 (NULL) 일 수 있음.
    NOT NULL 제약 (0003) 이 켜져 있으니 INSERT 가 실패해야 정상. 시드가 성공했다면
    seed.py 에서 ORM 이 _명시적으로_ 컬럼을 채우거나, default 가 있어야 함.

    학습 의도: 운영에선 _Expand 단계 직후_ 새 코드가 dual-write 하므로 신규 INSERT 도 컬럼 채움.
    여기선 _시드는 0001 까지만_ 정상이라는 한계를 명시 — 그러므로 시드 fixture 는 email_lower 를
    채우는 ORM 모델 확장이 필요. 단순화를 위해 본 테스트는 _스키마_ 검증만.
    """
    # 위 의도대로, 시드가 들어갔다면 모든 행에 email_lower 가 _존재_.
    null_count = (
        await seeded_session.execute(
            text("SELECT count(*) FROM deep_users WHERE email_lower IS NULL")
        )
    ).scalar_one()
    assert null_count == 0


async def test_alembic_history_has_three_revisions(seeded_session: AsyncSession) -> None:
    """alembic_version 에 0003 이 도달."""
    rev = (
        await seeded_session.execute(text("SELECT version_num FROM alembic_version"))
    ).scalar_one()
    assert rev == "0003"
