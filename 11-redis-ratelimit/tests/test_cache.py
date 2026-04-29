"""cache-aside 검증."""

from __future__ import annotations

import pytest
from cacheapp.cache import Cache

pytestmark = pytest.mark.integration


class TestCache:
    async def test_get_miss_returns_none(self, cache: Cache) -> None:
        assert await cache.get("missing") is None

    async def test_set_and_get(self, cache: Cache) -> None:
        await cache.set("k", {"x": 1})
        assert await cache.get("k") == {"x": 1}

    async def test_get_or_set_calls_loader_once(self, cache: Cache) -> None:
        calls = {"n": 0}

        async def loader() -> dict[str, int]:
            calls["n"] += 1
            return {"v": 42}

        # 첫 호출 — loader 실행
        v1 = await cache.get_or_set("k", loader)
        # 두 번째 — 캐시 hit, loader 실행 _안 함_
        v2 = await cache.get_or_set("k", loader)

        assert v1 == v2 == {"v": 42}
        assert calls["n"] == 1   # ← cache-aside 의 핵심 보장

    async def test_invalidate(self, cache: Cache) -> None:
        await cache.set("k", "value")
        deleted = await cache.invalidate("k")
        assert deleted == 1
        assert await cache.get("k") is None
