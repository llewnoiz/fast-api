"""e2e 테스트 — FastAPI + 진짜 Postgres + 진짜 Redis (testcontainers).

dependency_overrides 로 Settings 만 _컨테이너 URL_ 로 교체. 나머지는 그대로.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestE2E:
    async def test_create_then_get(self, app_client: AsyncClient) -> None:
        # 1) 생성
        r = await app_client.post("/items", json={"name": "Pencil", "price": 1500})
        assert r.status_code == 201
        created = r.json()
        assert created["name"] == "Pencil"
        item_id = created["id"]

        # 2) 조회
        r = await app_client.get(f"/items/{item_id}")
        assert r.status_code == 200
        assert r.json() == created

    async def test_get_missing_404(self, app_client: AsyncClient) -> None:
        r = await app_client.get("/items/9999")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"]

    async def test_validation_422(self, app_client: AsyncClient) -> None:
        # price 음수
        r = await app_client.post("/items", json={"name": "X", "price": -1})
        assert r.status_code == 422

    async def test_stats_aggregates_db_and_redis(self, app_client: AsyncClient) -> None:
        # 3개 만들고 각 1번 조회 → DB 합 + Redis 카운트 둘 다 확인
        for name, price in [("A", 1000), ("B", 2000), ("C", 500)]:
            r = await app_client.post("/items", json={"name": name, "price": price})
            assert r.status_code == 201
            await app_client.get(f"/items/{r.json()['id']}")

        r = await app_client.get("/stats")
        assert r.status_code == 200
        stats = r.json()
        assert stats["total_price"] == 3500       # DB 합계
        assert stats["hits_create"] == 3          # Redis 카운터
        assert stats["hits_get"] == 3
