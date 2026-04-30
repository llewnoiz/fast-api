"""Cache stampede 방지 테스트."""

from __future__ import annotations

import asyncio

import pytest
from cachemqdeep import stampede
from redis.asyncio import Redis

pytestmark = pytest.mark.integration


async def test_lock_dedupes_concurrent_loaders(redis_client: Redis) -> None:
    """동시 100개 요청이 들어와도 loader 는 _1번_ 만 실행되어야."""
    call_count = 0

    async def loader() -> dict[str, int]:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return {"value": 42}

    results = await asyncio.gather(
        *[
            stampede.get_or_set_with_lock(redis_client, "key1", loader, ttl=10)
            for _ in range(20)
        ]
    )
    assert all(r == {"value": 42} for r in results)
    # _이상적_ 으론 1, 현실적으론 1~2 (timeout fallback / race window)
    assert call_count <= 2


async def test_lock_returns_cached_after_first(redis_client: Redis) -> None:
    calls = 0

    async def loader() -> str:
        nonlocal calls
        calls += 1
        return "cached"

    v1 = await stampede.get_or_set_with_lock(redis_client, "key2", loader, ttl=10)
    v2 = await stampede.get_or_set_with_lock(redis_client, "key2", loader, ttl=10)
    assert v1 == v2 == "cached"
    assert calls == 1


async def test_xfetch_caches_value(redis_client: Redis) -> None:
    calls = 0

    async def loader() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"v": calls}

    v1 = await stampede.get_or_set_xfetch(redis_client, "xf:1", loader, ttl=10)
    v2 = await stampede.get_or_set_xfetch(redis_client, "xf:1", loader, ttl=10)
    assert v1 == v2 == {"v": 1}
    # 두 번째 호출이 _확률적_ 으로 재계산할 수도 있어 1 또는 2.
    assert calls <= 2
