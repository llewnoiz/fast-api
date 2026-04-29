"""FastAPI 앱 e2e — cache / lock / rate limit 라우트."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestCacheRoute:
    async def test_first_call_hits_external_second_uses_cache(self, app_client: AsyncClient) -> None:
        # 첫 호출 — 외부 API hit
        r1 = await app_client.get("/items/1")
        assert r1.status_code == 200

        s = (await app_client.get("/_stats/external_hits")).json()
        assert s["slow_api_calls"] == 1

        # 두 번째 호출 — 캐시 hit, 외부 API hit 증가 X
        r2 = await app_client.get("/items/1")
        assert r2.status_code == 200
        assert r2.json() == r1.json()  # 같은 응답 (TTL 안)

        s = (await app_client.get("/_stats/external_hits")).json()
        assert s["slow_api_calls"] == 1   # ← 여전히 1

    async def test_invalidate_then_refetch(self, app_client: AsyncClient) -> None:
        await app_client.get("/items/2")
        await app_client.post("/items/2/invalidate")
        await app_client.get("/items/2")

        s = (await app_client.get("/_stats/external_hits")).json()
        # 위 케이스에서 1, invalidate 후 다시 조회 1 — 총 2 (또는 그 이상, 위 케이스 영향)
        assert s["slow_api_calls"] >= 2


class TestRateLimit:
    async def test_blocks_after_limit(self, app_client: AsyncClient) -> None:
        # 5초 안에 3번 까지 — 4번째는 429
        for _ in range(3):
            r = await app_client.get("/limited")
            assert r.status_code == 200

        r = await app_client.get("/limited")
        assert r.status_code == 429   # Too Many Requests


class TestDistributedLockRoute:
    async def test_concurrent_same_order_blocks_one(self, app_client: AsyncClient) -> None:
        # 동시 두 호출 — 한 쪽은 200, 다른 쪽은 429
        import asyncio  # noqa: PLC0415

        r1, r2 = await asyncio.gather(
            app_client.post("/orders/100/process"),
            app_client.post("/orders/100/process"),
        )
        codes = sorted([r1.status_code, r2.status_code])
        assert codes == [200, 429]
