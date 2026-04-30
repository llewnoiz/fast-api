"""Postgres jsonb 활용 — GIN 인덱스 + 연산자.

연산자 치트시트:
    `tags @> '{"category": "tech"}'`     containment ── 가장 흔함, GIN 으로 빠름
    `tags ? 'category'`                  key 존재
    `tags ?| array['a','b']`             OR 키 존재
    `tags ?& array['a','b']`             AND 키 존재
    `tags -> 'labels'`                   jsonb 그대로 추출
    `tags ->> 'category'`                text 추출
    `tags #> '{labels,0}'`               경로 jsonb 추출
    `tags #>> '{labels,0}'`              경로 text 추출

GIN 인덱스 변형:
    `USING gin(tags)`                    기본 — 모든 연산자
    `USING gin(tags jsonb_path_ops)`     `@>` 만 — 더 작고 빠름 (대부분 충분)

비교:
    MySQL JSON_CONTAINS(...) — Postgres jsonb 가 _훨씬_ 풍부
    MongoDB find({tags: {$elemMatch: ...}}) — 비슷한 표현력
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from dbdeep.models import Post


async def find_posts_by_category(session: AsyncSession, category: str) -> list[Post]:
    """`tags @> '{"category": "X"}'` — GIN 인덱스 활용."""
    stmt = select(Post).where(Post.tags.op("@>")({"category": category}))
    return list((await session.scalars(stmt)).all())


async def find_posts_by_label(session: AsyncSession, label: str) -> list[Post]:
    """labels 배열에 _특정 값 포함_ — `tags @> '{"labels": ["fastapi"]}'`."""
    stmt = select(Post).where(Post.tags.op("@>")({"labels": [label]}))
    return list((await session.scalars(stmt)).all())


async def find_posts_with_min_views(session: AsyncSession, min_views: int) -> list[Post]:
    """`(tags->>'views')::int >= N` — text 추출 후 캐스팅. GIN 활용 X (B-tree 인덱스 별도 필요).

    교훈: jsonb 는 만능이 아님. _자주 쿼리되는 숫자 필드_ 는 보통 컬럼으로 빼는 게 정석.
    """
    stmt = select(Post).where(text("(tags->>'views')::int >= :min").bindparams(min=min_views))
    return list((await session.scalars(stmt)).all())


def deep_merge_jsonb_sql(column: str, patch: dict[str, Any]) -> Any:
    """jsonb _깊은_ 병합은 `||` 연산자로는 _얕은_ 병합만 됨. PG 의 `jsonb_set` 또는 함수 정의.

    학습용 — 03 의 jsonpath deep_merge 와 비교 (앱 레이어 vs DB 레이어).

    실무 가이드:
        - 키 _덮어쓰기_ 만 필요: `tags = tags || :patch::jsonb`
        - 깊은 병합: jsonb_recursive_merge 함수 (사용자 정의 PL/pgSQL) 또는 앱 레이어
    """
    raise NotImplementedError("학습용 placeholder — 실제 깊은 병합은 PL/pgSQL 또는 앱 레이어")
