"""Redis cache-aside — 11 단계 패턴 단순화."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis


class OrderCache:
    """주문 _개별_ 조회 캐시. 주문 생성 시 사용자별 _목록_ 캐시 무효화."""

    PREFIX = "tender:"

    def __init__(self, client: Redis, ttl: int = 60) -> None:
        self._c = client
        self._ttl = ttl

    @classmethod
    def order_key(cls, order_id: int) -> str:
        return f"{cls.PREFIX}order:{order_id}"

    @classmethod
    def user_orders_key(cls, user_id: int) -> str:
        return f"{cls.PREFIX}user:{user_id}:orders"

    async def get_order(self, order_id: int) -> dict[str, Any] | None:
        raw = await self._c.get(self.order_key(order_id))
        return json.loads(raw) if raw else None

    async def set_order(self, order_id: int, value: dict[str, Any]) -> None:
        await self._c.setex(self.order_key(order_id), self._ttl, json.dumps(value, default=str))

    async def invalidate_user_orders(self, user_id: int) -> None:
        """주문 생성 시 _사용자 목록_ 캐시 무효화 (write-through invalidation)."""
        await self._c.delete(self.user_orders_key(user_id))
