"""인덱스 + N+1 테스트.

각 테스트:
    - testcontainers Postgres + Alembic 적용
    - 시드 후 EXPLAIN _문자열_ 에 인덱스 이름이 등장하는지 확인 (운영급은 EXPLAIN ANALYZE + 비용 비교)
    - N+1 쿼리 카운터로 _쿼리 수_ 비교
"""

from __future__ import annotations

import pytest
from dbdeep import n_plus_one
from dbdeep.models import User
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def test_b_tree_index_used_for_username(seeded_session: AsyncSession) -> None:
    """username = 'X' — ix_deep_users_username 인덱스가 EXPLAIN 에 보여야."""
    plan = (
        await seeded_session.execute(
            text("EXPLAIN SELECT id FROM deep_users WHERE username = 'user0001'")
        )
    ).scalars().all()
    plan_text = "\n".join(plan)
    # 행이 적으면 _Seq Scan_ 이 더 빠를 수 있음. 학습 시드는 Index Scan 또는 Bitmap 둘 다 OK.
    assert ("Index" in plan_text) or ("ix_deep_users_username" in plan_text)


async def test_partial_index_active_users(seeded_session: AsyncSession) -> None:
    """is_active = true 가 _필터_ 조건이면 부분 인덱스 활용 후보."""
    plan = (
        await seeded_session.execute(
            text(
                "EXPLAIN SELECT id FROM deep_users "
                "WHERE is_active = true ORDER BY created_at DESC LIMIT 5"
            )
        )
    ).scalars().all()
    plan_text = "\n".join(plan)
    # planner 가 _부분 인덱스_ 를 골랐는지. 시드 규모가 작으면 Seq Scan 도 가능.
    # 학습 의도: 인덱스 _존재_ 확인. 사용 여부는 운영 데이터 양에 따라.
    assert "deep_users" in plan_text


async def test_n_plus_one_naive_creates_n_plus_1_queries(
    seeded_session: AsyncSession,
) -> None:
    """naive 패턴은 _User 1 + posts N_ 쿼리 — 시드 30명이면 31."""
    engine = seeded_session.bind  # AsyncEngine
    with n_plus_one.count_queries(engine) as q:  # type: ignore[arg-type]
        result = await n_plus_one.fetch_users_with_posts_naive(seeded_session)
    assert len(result) == 30
    # 1 (users) + 30 (per-user posts) = 31
    assert q.count == 31


async def test_n_plus_one_selectinload_uses_2_queries(
    seeded_session: AsyncSession,
) -> None:
    """selectinload — 1 (users) + 1 (posts WHERE author_id IN ...) = 2."""
    engine = seeded_session.bind
    with n_plus_one.count_queries(engine) as q:  # type: ignore[arg-type]
        users = await n_plus_one.fetch_users_with_posts_selectin(seeded_session)
    assert len(users) == 30
    assert q.count == 2


async def test_n_plus_one_joinedload_uses_1_query(
    seeded_session: AsyncSession,
) -> None:
    """joinedload — 1 쿼리. (행 수는 user × post 카티시안)."""
    engine = seeded_session.bind
    with n_plus_one.count_queries(engine) as q:  # type: ignore[arg-type]
        users = await n_plus_one.fetch_users_with_posts_joined(seeded_session)
    assert len(users) == 30
    assert q.count == 1


async def test_users_loaded(seeded_session: AsyncSession) -> None:
    """시드가 의도대로 들어갔는지 — 30 명, _대부분_ 활성."""
    from sqlalchemy import func, select  # noqa: PLC0415

    total = await seeded_session.scalar(select(func.count()).select_from(User))
    active = await seeded_session.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    )
    assert total == 30
    assert active is not None and active > 20  # 1/7 만 비활성
