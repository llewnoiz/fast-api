"""correlation-id 미들웨어 검증."""

from __future__ import annotations

from httpx import AsyncClient


class TestCorrelationId:
    async def test_generates_id_when_missing(self, app_client: AsyncClient) -> None:
        r = await app_client.get("/healthz")
        assert r.status_code == 200
        # 응답 헤더에 X-Request-ID 자동 포함
        rid = r.headers.get("x-request-id")
        assert rid and len(rid) >= 16   # uuid hex

    async def test_propagates_inbound_id(self, app_client: AsyncClient) -> None:
        # 요청에 들어온 X-Request-ID 가 _그대로_ 응답에 (분산 추적)
        r = await app_client.get("/healthz", headers={"X-Request-ID": "trace-abc-123"})
        assert r.status_code == 200
        assert r.headers["x-request-id"] == "trace-abc-123"
