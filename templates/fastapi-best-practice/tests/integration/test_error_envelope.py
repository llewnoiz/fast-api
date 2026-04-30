"""모든 에러가 ApiEnvelope `{code, message, data}` 형식 — 401/403/404/422/500."""

from __future__ import annotations

import pytest

from tests.conftest import signup_and_login

pytestmark = pytest.mark.integration


def _assert_envelope(body: dict) -> None:
    assert set(body.keys()) >= {"code", "message", "data"}
    assert isinstance(body["code"], str)
    assert isinstance(body["message"], str)


async def test_401_no_auth_envelope(app_client) -> None:
    r = await app_client.get("/api/v1/me")
    assert r.status_code == 401
    body = r.json()
    _assert_envelope(body)
    # OAuth2PasswordBearer 의 자동 401 → HTTPException → 핸들러
    assert body["code"].startswith("HTTP_") or body["code"] == "UNAUTHORIZED"


async def test_401_invalid_token_envelope(app_client) -> None:
    r = await app_client.get(
        "/api/v1/me", headers={"Authorization": "Bearer invalid"}
    )
    assert r.status_code == 401
    body = r.json()
    _assert_envelope(body)
    assert body["code"] == "UNAUTHORIZED"


async def test_403_forbidden_envelope(app_client) -> None:
    _, alice_h = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    _, bob_h = await signup_and_login(
        app_client, email="bob@example.com", username="bob"
    )

    create = await app_client.post(
        "/api/v1/items", json={"title": "x"}, headers=alice_h
    )
    item_id = create.json()["data"]["id"]

    r = await app_client.get(f"/api/v1/items/{item_id}", headers=bob_h)
    assert r.status_code == 403
    body = r.json()
    _assert_envelope(body)
    assert body["code"] == "FORBIDDEN"


async def test_404_not_found_envelope(app_client) -> None:
    _, headers = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    r = await app_client.get("/api/v1/items/99999", headers=headers)
    assert r.status_code == 404
    body = r.json()
    _assert_envelope(body)
    assert body["code"] == "NOT_FOUND"


async def test_409_conflict_envelope(app_client) -> None:
    await app_client.post(
        "/api/v1/users",
        json={"email": "dup@x.com", "username": "user1", "password": "password123"},
    )
    r = await app_client.post(
        "/api/v1/users",
        json={"email": "dup@x.com", "username": "user2", "password": "password123"},
    )
    assert r.status_code == 409
    body = r.json()
    _assert_envelope(body)
    assert body["code"] == "CONFLICT"


async def test_422_validation_envelope(app_client) -> None:
    r = await app_client.post(
        "/api/v1/users",
        json={"email": "not-an-email", "username": "u", "password": "short"},
    )
    assert r.status_code == 422
    body = r.json()
    _assert_envelope(body)
    assert body["code"] == "VALIDATION_ERROR"
    # 검증 디테일이 data.errors 에
    assert "errors" in body["data"]
