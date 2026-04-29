"""cache-aside 패턴 — _가장 흔한_ 캐시 전략.

흐름:
    1. cache.get(key) — 있으면 _그대로 반환_
    2. 없으면 source 에서 로드 (DB/외부 API)
    3. cache.set(key, value, ttl)
    4. 반환

비교:
    Spring:  @Cacheable("key") + RedisCacheManager
    NestJS:  CacheModule + cache.wrap(key, () => loader())
    Node:    ioredis + 직접 작성

다른 전략 (참고):
    write-through:    DB 쓸 때 _동시에_ cache 도. 최신성 ↑, 비용 ↑
    write-back:       cache 만 쓰고 나중에 DB. 빠름, 데이터 유실 위험
    write-around:     쓰기는 DB 만, 읽기 시 cache-aside. 자주 안 읽히는 데이터
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis


class Cache:
    """key prefix + JSON 직렬화 + TTL 통일."""

    def __init__(self, client: Redis, prefix: str = "app:", default_ttl: int = 60) -> None:
        self._client = client
        self._prefix = prefix
        self._default_ttl = default_ttl

    def _k(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(self._k(key))
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        await self._client.setex(self._k(key), ttl or self._default_ttl, json.dumps(value))

    async def delete(self, key: str) -> None:
        await self._client.delete(self._k(key))

    async def get_or_set(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        *,
        ttl: int | None = None,
    ) -> Any:
        """cache-aside 핵심 헬퍼.

        loader 는 _캐시 미스_ 일 때만 호출. 결과를 캐시에 저장 후 반환.
        """
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await loader()
        await self.set(key, value, ttl=ttl)
        return value

    async def invalidate(self, *keys: str) -> int:
        """write 시 _관련 캐시 키들_ 무효화. 핵심: write-through invalidation 패턴."""
        if not keys:
            return 0
        full = [self._k(k) for k in keys]
        deleted = await self._client.delete(*full)
        return int(deleted)
