"""07 — envelope + 에러 + 버전 관리 검증."""

from __future__ import annotations

from httpx import AsyncClient


# ---------- 공통 envelope ----------
class TestEnvelope:
    async def test_success_envelope_shape(self, client: AsyncClient) -> None:
        r = await client.get("/v2/orders/1")
        assert r.status_code == 200
        body = r.json()
        # envelope 의 3가지 키가 모두 있어야
        assert set(body.keys()) == {"code", "message", "data"}
        assert body["code"] == "OK"
        assert body["data"]["id"] == 1
        assert body["data"]["sku"] == "PEN-001"
        assert "created_at" in body["data"]

    async def test_envelope_on_validation_error(self, client: AsyncClient) -> None:
        # SKU 패턴 위반 → 422
        r = await client.post("/v2/orders", json={"sku": "lower", "quantity": 1})
        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert "errors" in body["data"]
        # Pydantic 의 errors 포맷이 그대로 전달되어야
        assert any("sku" in str(e["loc"]) for e in body["data"]["errors"])


# ---------- 도메인 예외 → 매핑된 status + 도메인 코드 ----------
class TestDomainErrors:
    async def test_not_found(self, client: AsyncClient) -> None:
        r = await client.get("/v2/orders/999")
        assert r.status_code == 404
        body = r.json()
        assert body["code"] == "ORDER_NOT_FOUND"
        assert "999" in body["message"]
        assert body["data"] is None

    async def test_out_of_stock_409(self, client: AsyncClient) -> None:
        r = await client.post("/v2/orders", json={"sku": "DISCONTINUED-001", "quantity": 1})
        assert r.status_code == 409
        body = r.json()
        assert body["code"] == "ORDER_OUT_OF_STOCK"
        # _status_ 와 _도메인 코드_ 분리: 같은 409 라도 코드로 분기 가능


# ---------- API 버전 관리 ----------
class TestVersioning:
    async def test_v1_has_deprecation_headers(self, client: AsyncClient) -> None:
        r = await client.get("/v1/orders/1")
        assert r.status_code == 200
        # v1 응답엔 Deprecation/Sunset/Link 헤더
        # httpx 의 headers 키는 _소문자로 정규화_ 됨 (HTTP/1.1 RFC 대응)
        assert r.headers.get("deprecation") == "true"
        assert r.headers.get("sunset")          # 값 존재 확인
        assert 'rel="successor-version"' in r.headers.get("link", "")

    async def test_v2_no_deprecation_headers(self, client: AsyncClient) -> None:
        r = await client.get("/v2/orders/1")
        assert r.status_code == 200
        assert "deprecation" not in r.headers

    async def test_v1_v2_have_different_schemas(self, client: AsyncClient) -> None:
        v1 = (await client.get("/v1/orders/1")).json()
        v2 = (await client.get("/v2/orders/1")).json()
        # v1: item / v2: sku
        assert "item" in v1["data"] and "sku" not in v1["data"]
        assert "sku" in v2["data"] and "item" not in v2["data"]
        # v2 만 created_at
        assert "created_at" in v2["data"]
        assert "created_at" not in v1["data"]

    async def test_v2_create_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/v2/orders", json={"sku": "PEN-002", "quantity": 3})
        assert r.status_code == 201
        body = r.json()
        assert body["code"] == "OK"
        assert body["message"] == "created"
        assert body["data"]["sku"] == "PEN-002"


# ---------- OpenAPI 노출 ----------
class TestOpenAPI:
    async def test_both_versions_in_spec(self, client: AsyncClient) -> None:
        spec = (await client.get("/openapi.json")).json()
        paths = spec["paths"]
        assert "/v1/orders/{order_id}" in paths
        assert "/v2/orders/{order_id}" in paths
        assert "/v1/orders" in paths
        assert "/v2/orders" in paths
