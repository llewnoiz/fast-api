"""15 통합 시나리오 — 04~14 의 모든 패턴이 _한 흐름_ 에서 동작.

시나리오:
    1. 사용자 등록 (시드)
    2. 로그인 → JWT
    3. /v2/orders 생성 — 검증/인증/DB 트랜잭션/outbox 기록
    4. 응답 envelope (fastapi-common ApiEnvelope) + correlation-id
    5. 동일 주문 GET — 첫 호출 DB, 두 번째는 캐시
    6. 잘못된 토큰 → 401 + envelope
    7. v1 호출 → deprecation 헤더
    8. v2 검증 실패 → 422 + envelope
    9. /v2/orders 재고 없음 → 409 + ORDER_OUT_OF_STOCK
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import login, register_user

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestEndToEndScenario:
    async def test_full_order_flow(self, app_client: AsyncClient) -> None:
        # 1) 사용자 시드
        await register_user(app_client, "alice", "alice123")

        # 2) 로그인
        token = await login(app_client, "alice", "alice123")
        headers = {"Authorization": f"Bearer {token}"}

        # 3) v2 주문 생성
        r = await app_client.post(
            "/v2/orders",
            json={"sku": "PEN-001", "quantity": 3},
            headers=headers,
        )
        assert r.status_code == 201
        body = r.json()
        # 4) envelope 형태 + correlation-id
        assert body["code"] == "OK"
        assert body["message"] == "ok"
        assert body["data"]["sku"] == "PEN-001"
        assert "x-request-id" in r.headers
        order_id = body["data"]["id"]

        # 5) 캐시 동작 — 같은 주문 두 번 GET, 둘 다 같은 응답
        r1 = await app_client.get(f"/v2/orders/{order_id}", headers=headers)
        r2 = await app_client.get(f"/v2/orders/{order_id}", headers=headers)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["data"] == r2.json()["data"]

    async def test_unauthorized_returns_envelope(self, app_client: AsyncClient) -> None:
        r = await app_client.get("/v2/orders/1")
        assert r.status_code == 401
        body = r.json()
        # envelope 모양 (fastapi-common 핸들러).
        # OAuth2PasswordBearer 의 자동 401 은 HTTP_401 코드 (HTTPException 경로),
        # 토큰 _위조_ 케이스만 UNAUTHORIZED (도메인 AuthError 경로) — 둘 다 envelope.
        assert body["code"] in ("UNAUTHORIZED", "HTTP_401")
        assert "code" in body and "message" in body and "data" in body

    async def test_invalid_token_envelope(self, app_client: AsyncClient) -> None:
        r = await app_client.get("/v2/orders/1", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 401
        assert r.json()["code"] == "UNAUTHORIZED"

    async def test_v1_has_deprecation_headers(self, app_client: AsyncClient) -> None:
        await register_user(app_client, "bob", "bob123")
        token = await login(app_client, "bob", "bob123")

        r = await app_client.post(
            "/v1/orders",
            json={"item": "pencil", "quantity": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        assert r.headers.get("deprecation") == "true"
        assert r.headers.get("sunset")
        assert "successor-version" in r.headers.get("link", "")

    async def test_validation_422_envelope(self, app_client: AsyncClient) -> None:
        await register_user(app_client, "carol", "carol123")
        token = await login(app_client, "carol", "carol123")

        # sku 패턴 위반
        r = await app_client.post(
            "/v2/orders",
            json={"sku": "lower", "quantity": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "VALIDATION_ERROR"

    async def test_out_of_stock_409_envelope(self, app_client: AsyncClient) -> None:
        await register_user(app_client, "dave", "dave123")
        token = await login(app_client, "dave", "dave123")

        r = await app_client.post(
            "/v2/orders",
            json={"sku": "DISCONTINUED-001", "quantity": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "ORDER_OUT_OF_STOCK"
