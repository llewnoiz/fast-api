"""N+1 문제 시연 — naive vs selectinload vs joinedload.

문제:
    "User 100명 + 각자의 Post 목록" 을 가져올 때 _초보 코드_ 는 1 + 100 = 101 쿼리 발생.
    eager loading 으로 1~2 쿼리로 압축해야 함.

용어:
    - **lazy** (기본): 관계 접근 _시점_ 에 별도 쿼리 (N+1 의 원흉)
    - **selectinload**: 부모 ID 모아 `WHERE id IN (...)` 한 번 (총 _2_ 쿼리)
    - **joinedload**: LEFT JOIN 으로 한 번에 (총 _1_ 쿼리, but 카티시안 곱 위험)

선택 가이드:
    - 1:N (자식이 많을 때) → **selectinload**  ← 거의 항상 정답
    - N:1 (부모 단일) → **joinedload** OK
    - 카디널리티 폭발 (M:N 또는 깊은 트리) → **selectinload** (joinedload 는 결과 row 수 폭증)

비교:
    Spring Data JPA: `@EntityGraph(attributePaths = {"posts"})` 또는 `JOIN FETCH`
    NestJS TypeORM:  `relations: ["posts"]` 또는 QueryBuilder `leftJoinAndSelect`
    Hibernate:       `FetchType.LAZY` 기본 → `JOIN FETCH` 로 명시적 eager
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from dbdeep.models import Post, User


@dataclass
class QueryCounter:
    """SELECT 문 _개수_ 카운터 — N+1 검출용.

    실무에선 SQLAlchemy `before_cursor_execute` 이벤트를 _쓰는 패턴이 정석_.
    """

    count: int = 0


@contextmanager
def count_queries(engine: AsyncEngine | Engine) -> Iterator[QueryCounter]:
    """`with count_queries(engine) as q: ...; assert q.count == 2` 식으로 사용.

    AsyncEngine 이면 `engine.sync_engine` 에 이벤트를 건다 — 실제 쿼리는 sync 레이어에서 실행.
    """
    counter = QueryCounter()
    sync_engine = engine.sync_engine if isinstance(engine, AsyncEngine) else engine

    def _before_cursor(conn, cursor, statement, params, context, executemany):  # noqa: ANN001, ANN202
        # SELECT 만 카운트 — INSERT/UPDATE 까지 세면 노이즈
        if statement.lstrip().upper().startswith("SELECT"):
            counter.count += 1

    event.listen(sync_engine, "before_cursor_execute", _before_cursor)
    try:
        yield counter
    finally:
        event.remove(sync_engine, "before_cursor_execute", _before_cursor)


# ─────────────────────────────────────────────────────────────────
# 패턴 1 — naive (N+1): User 가져오고, 루프에서 user.posts 접근 → 매번 쿼리
# 주의: SQLAlchemy 2.0 async 는 lazy load 를 _기본 비허용_ (MissingGreenlet 발생).
#       즉 코드가 _명시적으로_ eager load 하도록 강제. 좋은 디자인.
#       이 함수는 _학습용_ 으로 명시적 .awaitable_attrs 또는 별도 쿼리로 N+1 재현.
# ─────────────────────────────────────────────────────────────────
async def fetch_users_with_posts_naive(session: AsyncSession) -> list[tuple[User, list[Post]]]:
    """N+1 재현 — User 1쿼리 + 각 user 마다 Post 1쿼리. 의도적으로 비효율."""
    users = (await session.scalars(select(User))).all()
    result: list[tuple[User, list[Post]]] = []
    for u in users:
        posts = (await session.scalars(select(Post).where(Post.author_id == u.id))).all()
        result.append((u, list(posts)))
    return result


# ─────────────────────────────────────────────────────────────────
# 패턴 2 — selectinload: 1 + 1 = 2 쿼리. _거의 항상_ 정답.
# ─────────────────────────────────────────────────────────────────
async def fetch_users_with_posts_selectin(session: AsyncSession) -> list[User]:
    stmt = select(User).options(selectinload(User.posts))
    return list((await session.scalars(stmt)).all())


# ─────────────────────────────────────────────────────────────────
# 패턴 3 — joinedload: 1 쿼리 (LEFT JOIN). 행 수 폭증 가능.
# ─────────────────────────────────────────────────────────────────
async def fetch_users_with_posts_joined(session: AsyncSession) -> list[User]:
    stmt = select(User).options(joinedload(User.posts)).distinct()
    # 1:N joinedload 시 unique() 필수 — User 가 Post 수만큼 중복되니 dedupe.
    return list((await session.scalars(stmt)).unique().all())
