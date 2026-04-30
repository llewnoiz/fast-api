"""FastAPI 어댑터 e2e — HTTP 엔드포인트로 use case 호출.

기억할 것: FastAPI 는 _하나의 어댑터_. 같은 use case 를 GraphQL / CLI / message handler 로도 노출 가능.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200


def test_place_order_201(client: TestClient) -> None:
    r = client.post(
        "/orders",
        json={
            "user_id": 1,
            "lines": [
                {"sku": "ABC-0001", "quantity": 2, "unit_amount": 1000, "currency": "KRW"}
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["total_amount"] == 2000


def test_place_order_invalid_sku_400(client: TestClient) -> None:
    """도메인 InvariantViolation → 400."""
    r = client.post(
        "/orders",
        json={
            "user_id": 1,
            "lines": [
                {"sku": "abc-0001", "quantity": 1, "unit_amount": 100, "currency": "KRW"}
            ],
        },
    )
    assert r.status_code == 400


def test_place_order_unknown_user_404(client: TestClient) -> None:
    r = client.post(
        "/orders",
        json={
            "user_id": 9999,
            "lines": [
                {"sku": "ABC-0001", "quantity": 1, "unit_amount": 100, "currency": "KRW"}
            ],
        },
    )
    assert r.status_code == 404


def test_get_order(client: TestClient) -> None:
    place = client.post(
        "/orders",
        json={
            "user_id": 1,
            "lines": [
                {"sku": "ABC-0001", "quantity": 3, "unit_amount": 200, "currency": "KRW"}
            ],
        },
    )
    order_id = place.json()["order_id"]

    r = client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "PLACED"
    assert body["total_amount"] == 600
    assert len(body["lines"]) == 1


def test_cancel_order_204(client: TestClient) -> None:
    place = client.post(
        "/orders",
        json={
            "user_id": 1,
            "lines": [
                {"sku": "ABC-0001", "quantity": 1, "unit_amount": 100, "currency": "KRW"}
            ],
        },
    )
    order_id = place.json()["order_id"]

    r = client.post(f"/orders/{order_id}/cancel", json={"reason": "test"})
    assert r.status_code == 204

    detail = client.get(f"/orders/{order_id}").json()
    assert detail["status"] == "CANCELLED"


def test_cancel_unknown_order_404(client: TestClient) -> None:
    r = client.post("/orders/9999/cancel", json={"reason": "x"})
    assert r.status_code == 404


def test_get_unknown_order_404(client: TestClient) -> None:
    r = client.get("/orders/9999")
    assert r.status_code == 404
