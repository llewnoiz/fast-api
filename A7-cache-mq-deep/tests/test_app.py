"""FastAPI e2e 테스트 — 7가지 패턴 라우트."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_healthz(app_client: AsyncClient) -> None:
    r = await app_client.get("/healthz")
    assert r.status_code == 200


async def test_stampede_endpoint(app_client: AsyncClient) -> None:
    r = await app_client.get("/stampede/k1")
    assert r.status_code == 200
    assert r.json()["value"] == {"computed": "k1"}


async def test_xfetch_endpoint(app_client: AsyncClient) -> None:
    r = await app_client.get("/xfetch/k2")
    assert r.status_code == 200


async def test_saga_success(app_client: AsyncClient) -> None:
    r = await app_client.post("/saga/checkout")
    assert r.status_code == 200
    body = r.json()
    assert body["succeeded"] is True
    assert body["completed"] == ["charge", "reserve", "ship"]
    assert body["compensated"] == []


async def test_saga_compensation_on_ship_failure(app_client: AsyncClient) -> None:
    r = await app_client.post("/saga/checkout", params={"fail_at": "ship"})
    body = r.json()
    assert body["succeeded"] is False
    assert body["completed"] == ["charge", "reserve"]
    assert body["compensated"] == ["reserve", "charge"]


async def test_cqrs_command_then_query(app_client: AsyncClient) -> None:
    cmd = await app_client.post(
        "/cqrs/order", json={"user_id": 5, "item": "tea", "quantity": 3}
    )
    assert cmd.status_code == 200

    q = await app_client.get("/cqrs/summary/5")
    assert q.status_code == 200
    body = q.json()
    assert body["total_orders"] == 1
    assert body["total_quantity"] == 3


async def test_event_sourcing_flow(app_client: AsyncClient) -> None:
    await app_client.post("/es/A1/open", params={"opening_balance": 0})
    await app_client.post("/es/A1/deposit", params={"amount": 100})
    await app_client.post("/es/A1/deposit", params={"amount": 50})
    r = await app_client.get("/es/A1/balance")
    assert r.status_code == 200
    body = r.json()
    assert body["balance"] == 150
    assert body["events"] == 3


async def test_event_sourcing_overdraft_400(app_client: AsyncClient) -> None:
    await app_client.post("/es/A2/open", params={"opening_balance": 10})
    r = await app_client.post("/es/A2/withdraw", params={"amount": 999})
    assert r.status_code == 400


async def test_schema_register_and_get(app_client: AsyncClient) -> None:
    schema = {
        "type": "object",
        "properties": {"order_id": {"type": "integer"}},
        "required": ["order_id"],
    }
    r1 = await app_client.post(
        "/schema/register", json={"subject": "Order", "schema_def": schema}
    )
    assert r1.status_code == 200
    assert r1.json()["version"] == 1

    r2 = await app_client.get("/schema/Order/latest")
    assert r2.status_code == 200
    assert r2.json()["schema"]["properties"]["order_id"]["type"] == "integer"
