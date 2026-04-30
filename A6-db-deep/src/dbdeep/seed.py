"""학습용 시드 데이터 — 인덱스/N+1 효과를 _체감_ 할 수준의 데이터.

규모:
    - User: 100명
    - Post: 1,000개 (User 당 평균 10개)
    - Comment: 5,000개 (Post 당 평균 5개)

소규모지만 EXPLAIN 으로 인덱스 사용 vs Seq Scan 차이를 보기엔 충분.
운영급 측정은 _수백만 행_ 으로 — 학습용은 패턴 익히는 게 목표.
"""

from __future__ import annotations

import json
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbdeep.models import Comment, Post, User

CATEGORIES = ["tech", "life", "music", "food", "travel", "code"]
TAG_WORDS = ["fastapi", "python", "postgres", "redis", "kafka", "async", "ddd", "k8s"]


async def seed_data(session: AsyncSession, *, users: int = 100, posts_per_user: int = 10) -> None:
    """이미 시드된 경우 _건너뜀_ (idempotent — 테스트에서 여러 번 호출 가능)."""
    existing = await session.scalar(select(User).limit(1))
    if existing is not None:
        return

    rng = random.Random(42)  # 재현성

    # ── User
    user_objs = [
        User(
            username=f"user{i:04d}",
            email=f"u{i}@example.com",
            email_lower=f"u{i}@example.com",  # dual-write — Expand-Contract 의 phase 2
            is_active=(i % 7 != 0),
        )
        for i in range(users)
    ]
    session.add_all(user_objs)
    await session.flush()

    # ── Post — author 별로 시간 분산
    post_objs: list[Post] = []
    for u in user_objs:
        for j in range(posts_per_user):
            cat = rng.choice(CATEGORIES)
            tag_list = rng.sample(TAG_WORDS, k=rng.randint(1, 3))
            post_objs.append(
                Post(
                    author_id=u.id,
                    title=f"{u.username} post {j} — {cat}",
                    body=f"Body of post {j} talking about {cat} and {' '.join(tag_list)}.",
                    tags={"category": cat, "labels": tag_list, "views": rng.randint(0, 1000)},
                )
            )
    session.add_all(post_objs)
    await session.flush()

    # ── Comment
    comment_objs = [
        Comment(post_id=p.id, body=f"comment {k} on post {p.id}")
        for p in post_objs
        for k in range(rng.randint(0, 8))
    ]
    session.add_all(comment_objs)
    await session.commit()

    # tsvector 갱신 — 마이그레이션의 GENERATED ALWAYS AS 가 자동 처리하지만,
    # 학습용으로 _수동 UPDATE_ 도 보여줌. 마이그레이션이 이미 처리하면 no-op.
    # (실제 동작은 fts.py 에서 명시적 검색)


def parse_tags(raw: str | dict[str, object]) -> dict[str, object]:
    """API 입력으로 들어온 tags 를 dict 로 정규화 (학습용 헬퍼)."""
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)
