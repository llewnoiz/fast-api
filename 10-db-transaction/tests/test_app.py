"""FastAPI 풀 스택 — 라우트 → UoW → DB."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestApp:
    async def test_create_user_and_list(self, app_client: AsyncClient) -> None:
        r = await app_client.post("/users", json={"username": "alice", "full_name": "Alice K"})
        assert r.status_code == 201
        u = r.json()
        assert u["username"] == "alice"

        r = await app_client.get("/users")
        assert r.status_code == 200
        users = r.json()
        assert len(users) == 1
        assert users[0]["orders"] == []

    async def test_create_orders_for_user(self, app_client: AsyncClient) -> None:
        r = await app_client.post("/users", json={"username": "bob", "full_name": "Bob"})
        user_id = r.json()["id"]

        for item, qty in [("Pencil", 2), ("Notebook", 1)]:
            r = await app_client.post(
                f"/users/{user_id}/orders",
                json={"item": item, "quantity": qty},
            )
            assert r.status_code == 201

        r = await app_client.get("/users")
        users = r.json()
        assert len(users[0]["orders"]) == 2

    async def test_order_for_missing_user_404(self, app_client: AsyncClient) -> None:
        r = await app_client.post("/users/9999/orders", json={"item": "X", "quantity": 1})
        assert r.status_code == 404
