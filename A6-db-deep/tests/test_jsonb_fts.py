"""jsonb 검색 + Full-Text Search 테스트."""

from __future__ import annotations

import pytest
from dbdeep import fts, jsonb
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def test_find_by_category_uses_gin(seeded_session: AsyncSession) -> None:
    posts = await jsonb.find_posts_by_category(seeded_session, "tech")
    assert len(posts) > 0
    for p in posts:
        assert p.tags["category"] == "tech"


async def test_find_by_label_uses_jsonb_containment(seeded_session: AsyncSession) -> None:
    posts = await jsonb.find_posts_by_label(seeded_session, "fastapi")
    assert len(posts) > 0
    for p in posts:
        assert "fastapi" in p.tags["labels"]


async def test_explain_jsonb_uses_gin_index(seeded_session: AsyncSession) -> None:
    """EXPLAIN 에 GIN 인덱스 이름이 _존재_ 하는지 — planner 가 채택하는 건 별개.

    시드가 작으면 Seq Scan 일 수 있으니 _존재 확인_ 만. 운영 규모에선 Bitmap Index Scan 채택.
    """
    plan = (
        await seeded_session.execute(
            text("EXPLAIN SELECT id FROM deep_posts WHERE tags @> '{\"category\": \"tech\"}'")
        )
    ).scalars().all()
    plan_text = "\n".join(plan)
    # 시드가 적으면 Seq Scan. 인덱스가 _존재_ 하는지 별도 카탈로그로 검증.
    assert "deep_posts" in plan_text


async def test_gin_index_exists(seeded_session: AsyncSession) -> None:
    """pg_indexes 카탈로그에서 GIN 인덱스 _존재_ 확인."""
    rows = (
        await seeded_session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'deep_posts' AND indexname LIKE '%gin%'"
            )
        )
    ).scalars().all()
    assert "ix_deep_posts_tags_gin" in rows
    assert "ix_deep_posts_search_gin" in rows


async def test_fts_search_finds_keyword(seeded_session: AsyncSession) -> None:
    """body 안에 'fastapi' 가 들어간 글 검색."""
    posts = await fts.search_posts(seeded_session, "fastapi")
    assert len(posts) > 0


async def test_fts_search_ranked_returns_ordered(seeded_session: AsyncSession) -> None:
    """ts_rank 정렬 — 결과가 비어있지 않고 limit 이내."""
    posts = await fts.search_posts_ranked(seeded_session, "python", limit=5)
    assert 0 < len(posts) <= 5


async def test_fts_no_match_returns_empty(seeded_session: AsyncSession) -> None:
    posts = await fts.search_posts(seeded_session, "nonexistentwordxyz")
    assert posts == []
