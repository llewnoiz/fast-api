"""Redis 캐시 — redis.asyncio.

11 단계 (Redis + Rate Limit) 에서 _본격_ 다룸. 여기선 _테스트 대상_ 으로 단순 get/set.
"""

from __future__ import annotations

from redis.asyncio import Redis


class HitCounter:
    """엔드포인트별 히트 카운트 — Redis INCR 사용 (atomic)."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    @staticmethod
    def _key(name: str) -> str:
        return f"hits:{name}"

    async def hit(self, name: str) -> int:
        """카운터 1 증가. 새 키면 0 → 1."""
        return await self._client.incr(self._key(name))

    async def get(self, name: str) -> int:
        v = await self._client.get(self._key(name))
        return int(v) if v is not None else 0

    async def reset(self, name: str) -> None:
        await self._client.delete(self._key(name))
