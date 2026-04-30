"""Redis cache-aside — Item 캐시.

패턴 (cache-aside, write-through invalidation):
    - GET 단일 → 캐시 hit 우선, miss 시 DB → 캐시 set
    - POST/PUT/DELETE → DB 변경 후 _캐시 무효화_

확장:
    - stampede 방지 (lock-based 또는 XFetch) → A7 참고
    - 분산 캐시 무효화 (다중 인스턴스) → Redis pub/sub 또는 LISTEN/NOTIFY
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis


class ItemCache:
    PREFIX = "app:"

    def __init__(self, client: Redis, *, ttl: int = 60) -> None:
        self._c = client
        self._ttl = ttl

    @classmethod
    def item_key(cls, item_id: int) -> str:
        return f"{cls.PREFIX}item:{item_id}"

    @classmethod
    def user_items_key(cls, user_id: int) -> str:
        return f"{cls.PREFIX}user:{user_id}:items"

    async def get_item(self, item_id: int) -> dict[str, Any] | None:
        raw = await self._c.get(self.item_key(item_id))
        return json.loads(raw) if raw else None

    async def set_item(self, item_id: int, value: dict[str, Any]) -> None:
        await self._c.setex(
            self.item_key(item_id), self._ttl, json.dumps(value, default=str)
        )

    async def invalidate_item(self, item_id: int) -> None:
        await self._c.delete(self.item_key(item_id))

    async def invalidate_user_items(self, user_id: int) -> None:
        await self._c.delete(self.user_items_key(user_id))
