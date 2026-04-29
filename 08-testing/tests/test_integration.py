"""integration 테스트 — testcontainers 로 _진짜_ Postgres / Redis.

도커 데몬 안 켜져 있으면 conftest 의 fixture 가 _자동 스킵_. unit 만 돌고 끝.

장점:
    - SQLite 같은 _다른 DB_ 가짜 흉내 없이 _진짜 환경_ 검증
    - 마이그레이션 / 인덱스 / 제약조건 _실제로_ 동작
    - 도커 떠 있는 동안만 살아있어서 격리 + 정리 자동

단점:
    - 도커 시작 시간 (수 초) — session-scope 로 _전체 한 번_ 만 띄움
    - 디스크 / 메모리 사용
"""

from __future__ import annotations

import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis
from testapp.cache import HitCounter
from testapp.repository import ItemRepository

pytestmark = pytest.mark.integration


# ---------- Postgres ----------
class TestPostgresRepository:
    async def test_add_and_get(self, db_conn: AsyncConnection) -> None:
        repo = ItemRepository(db_conn)
        await repo.init_schema()
        await repo.clear()

        item = await repo.add("Pencil", 1500)
        assert item.id == 1
        assert item.name == "Pencil"
        assert item.price == 1500

        got = await repo.get(item.id)
        assert got == item

    async def test_get_missing_returns_none(self, db_conn: AsyncConnection) -> None:
        repo = ItemRepository(db_conn)
        await repo.init_schema()
        await repo.clear()
        assert await repo.get(999) is None

    async def test_total(self, db_conn: AsyncConnection) -> None:
        repo = ItemRepository(db_conn)
        await repo.init_schema()
        await repo.clear()

        await repo.add("A", 1000)
        await repo.add("B", 2000)
        await repo.add("C", 500)

        assert await repo.total() == 3500

    async def test_negative_price_rejected_by_db_check(self, db_conn: AsyncConnection) -> None:
        """DB 의 CHECK 제약 — 마이그레이션이 _진짜로_ 동작하는지 검증."""
        repo = ItemRepository(db_conn)
        await repo.init_schema()
        await repo.clear()

        from psycopg.errors import CheckViolation  # noqa: PLC0415

        with pytest.raises(CheckViolation):
            await repo.add("Bad", -1)


# ---------- Redis ----------
class TestRedisCounter:
    async def test_hit_increments(self, redis_client: Redis) -> None:
        c = HitCounter(redis_client)
        assert await c.hit("foo") == 1
        assert await c.hit("foo") == 2
        assert await c.hit("foo") == 3

    async def test_isolated_keys(self, redis_client: Redis) -> None:
        c = HitCounter(redis_client)
        await c.hit("a")
        await c.hit("a")
        await c.hit("b")
        assert await c.get("a") == 2
        assert await c.get("b") == 1

    async def test_reset(self, redis_client: Redis) -> None:
        c = HitCounter(redis_client)
        await c.hit("x")
        await c.reset("x")
        assert await c.get("x") == 0
