"""04 단계 라우트 테스트."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ---------- 헬스체크 ----------
class TestHealth:
    @pytest.mark.asyncio
    async def test_healthz(self, client: AsyncClient) -> None:
        r = await client.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "app" in body and "version" in body and "env" in body

    @pytest.mark.asyncio
    async def test_readyz(self, client: AsyncClient) -> None:
        r = await client.get("/readyz")
        assert r.status_code == 200
        assert r.json() == {"status": "ready"}


# ---------- 아이템 ----------
class TestItems:
    @pytest.mark.asyncio
    async def test_list_default(self, client: AsyncClient) -> None:
        r = await client.get("/items")
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_list_in_stock_filter(self, client: AsyncClient) -> None:
        r = await client.get("/items", params={"in_stock_only": "true"})
        assert r.status_code == 200
        items = r.json()
        assert all(i["in_stock"] for i in items)
        assert len(items) == 2  # Eraser 제외

    @pytest.mark.asyncio
    async def test_list_limit_validation(self, client: AsyncClient) -> None:
        # limit=0 은 ge=1 위반 → 422 자동
        r = await client.get("/items", params={"limit": 0})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_get_one_ok(self, client: AsyncClient) -> None:
        r = await client.get("/items/1")
        assert r.status_code == 200
        assert r.json()["name"] == "Pencil"

    @pytest.mark.asyncio
    async def test_get_one_not_found(self, client: AsyncClient) -> None:
        r = await client.get("/items/999")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_one_path_validation(self, client: AsyncClient) -> None:
        # path 가 int 가 아니면 422
        r = await client.get("/items/abc")
        assert r.status_code == 422


# ---------- echo (요청 본문 검증) ----------
class TestEcho:
    @pytest.mark.asyncio
    async def test_echo_default(self, client: AsyncClient) -> None:
        r = await client.post("/echo", json={"message": "hi"})
        assert r.status_code == 200
        body = r.json()
        assert body["echoed"] == ["hi"]
        assert "received_at" in body

    @pytest.mark.asyncio
    async def test_echo_repeat(self, client: AsyncClient) -> None:
        r = await client.post("/echo", json={"message": "hi", "repeat": 3})
        assert r.status_code == 200
        assert r.json()["echoed"] == ["hi", "hi", "hi"]

    @pytest.mark.asyncio
    async def test_echo_validation_empty_message(self, client: AsyncClient) -> None:
        r = await client.post("/echo", json={"message": "", "repeat": 1})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_echo_validation_repeat_too_large(self, client: AsyncClient) -> None:
        r = await client.post("/echo", json={"message": "hi", "repeat": 99})
        assert r.status_code == 422


# ---------- OpenAPI / docs ----------
class TestOpenAPI:
    @pytest.mark.asyncio
    async def test_openapi_json(self, client: AsyncClient) -> None:
        r = await client.get("/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert spec["info"]["title"] == "fastapi-hello"
        # 등록한 모든 라우트가 스펙에 노출되어야 함
        paths = spec["paths"]
        assert "/healthz" in paths
        assert "/readyz" in paths
        assert "/items" in paths
        assert "/items/{item_id}" in paths
        assert "/echo" in paths

    @pytest.mark.asyncio
    async def test_swagger_ui_html(self, client: AsyncClient) -> None:
        r = await client.get("/docs")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
