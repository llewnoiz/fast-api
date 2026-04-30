"""Postgres Full-Text Search — tsvector + tsquery.

핵심 개념:
    - **tsvector**: 단어를 _정규화_ (lowercase, stemming, stop-word 제거) 한 표현
    - **tsquery**: 검색식 — `to_tsquery('python & fastapi')` (AND), `'python | go'` (OR)
    - **plainto_tsquery**: 사용자 입력을 _안전하게_ tsquery 로 (공백 = AND)
    - **websearch_to_tsquery**: 구글 스타일 — `"exact phrase" -minus +plus`

인덱스:
    GIN(search) — 가장 흔함, 검색 빠름. 쓰기 비용 ↑.
    GiST(search) — 작고 _업데이트 친화_, 검색 좀 느림.

저장 vs 즉시 계산:
    - 저장 (tsvector 컬럼 + GENERATED ALWAYS AS): 빠름, 디스크 ↑
    - 즉시 계산 (`to_tsvector('english', body)`): 디스크 절약, 매번 인덱스 재계산 ─ 반대.
    → 보통 _저장_ 이 정답. 본 학습 모델도 `search` 컬럼 + GIN 인덱스.

비교:
    MySQL FULLTEXT — Postgres FTS 가 _다국어 / 가중치 / phrase / 랭킹_ 에서 우월
    Elasticsearch — 운영급 검색은 ES 가 정답. PG FTS 는 _중간 규모_ 까지 적합.
    SQLite FTS5 — 비슷한 모델 (가상 테이블)
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dbdeep.models import Post


async def search_posts(session: AsyncSession, query: str) -> list[Post]:
    """`websearch_to_tsquery` — 구글 스타일 (자연스러운 사용자 입력)."""
    tsq = func.websearch_to_tsquery("english", query)
    stmt = select(Post).where(Post.search.op("@@")(tsq))
    return list((await session.scalars(stmt)).all())


async def search_posts_ranked(session: AsyncSession, query: str, limit: int = 10) -> list[Post]:
    """관련도 순 정렬 — `ts_rank` 가 표준.

    실무 팁: `ts_rank_cd` (cover density) 도 있음 — 단어 _근접성_ 가중. 일반 ts_rank 면 충분.
    """
    tsq = func.websearch_to_tsquery("english", query)
    rank = func.ts_rank(Post.search, tsq).label("rank")
    stmt = (
        select(Post, rank)
        .where(Post.search.op("@@")(tsq))
        .order_by(rank.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [row[0] for row in rows]
