"""아이템 repository — Postgres async 클라이언트 (psycopg 3).

10 단계 (DB+트랜잭션) 에서 SQLAlchemy 로 _업그레이드_. 여기선 _테스트 학습용_ 으로
가볍게 raw SQL.

비교:
    Spring:    JdbcTemplate 또는 JPA Repository
    NestJS:    typeorm Repository
    Kotlin:    Exposed / R2DBC
    Node:      pg, knex, prisma
"""

from __future__ import annotations

from dataclasses import dataclass

from psycopg import AsyncConnection
from psycopg.rows import dict_row


@dataclass(frozen=True)
class Item:
    id: int
    name: str
    price: int


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0)
);
"""


class ItemRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def init_schema(self) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(SCHEMA_SQL)
        await self._conn.commit()

    async def add(self, name: str, price: int) -> Item:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "INSERT INTO items(name, price) VALUES (%s, %s) RETURNING id, name, price",
                (name, price),
            )
            row = await cur.fetchone()
        await self._conn.commit()
        assert row is not None
        return Item(**row)

    async def get(self, item_id: int) -> Item | None:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT id, name, price FROM items WHERE id = %s", (item_id,))
            row = await cur.fetchone()
        return Item(**row) if row else None

    async def total(self) -> int:
        """가격 합계 — 도메인 로직 _테스트 대상_ 의 한 예."""
        async with self._conn.cursor() as cur:
            await cur.execute("SELECT COALESCE(SUM(price), 0) FROM items")
            row = await cur.fetchone()
        assert row is not None
        return int(row[0])

    async def clear(self) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute("TRUNCATE items RESTART IDENTITY")
        await self._conn.commit()


# ============================================================================
# _순수_ 도메인 로직 — DB 없이 unit 테스트 가능
# ============================================================================


def discounted_price(original: int, percent: int) -> int:
    """할인 가격 계산. unit 테스트 대상 — 외부 의존성 0."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be in 0..100")
    return original * (100 - percent) // 100
