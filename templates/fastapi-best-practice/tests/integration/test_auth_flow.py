"""인증 플로우 e2e — signup → login → /me + 에러 시나리오."""

from __future__ import annotations

import pytest

from tests.conftest import login_user, signup_and_login, signup_user

pytestmark = pytest.mark.integration


async def test_signup_login_me(app_client) -> None:
    user, headers = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    assert user["email"] == "alice@example.com"
    assert user["username"] == "alice"
    assert user["role"] == "user"
    assert user["is_active"] is True

    r = await app_client.get("/api/v1/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "OK"
    assert body["data"]["email"] == "alice@example.com"


async def test_signup_returns_envelope_201(app_client) -> None:
    r = await app_client.post(
        "/api/v1/users",
        json={
            "email": "bob@example.com",
            "username": "bob",
            "password": "password123",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["code"] == "OK"
    assert body["message"] == "created"
    assert "data" in body


async def test_signup_duplicate_email_409(app_client) -> None:
    await signup_user(
        app_client, email="dup@example.com", username="user1"
    )
    r = await app_client.post(
        "/api/v1/users",
        json={
            "email": "dup@example.com",
            "username": "user2",
            "password": "password123",
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "CONFLICT"


async def test_signup_duplicate_username_409(app_client) -> None:
    await signup_user(app_client, email="a@example.com", username="dupname")
    r = await app_client.post(
        "/api/v1/users",
        json={
            "email": "b@example.com",
            "username": "dupname",
            "password": "password123",
        },
    )
    assert r.status_code == 409


async def test_signup_short_password_422(app_client) -> None:
    r = await app_client.post(
        "/api/v1/users",
        json={"email": "x@example.com", "username": "x", "password": "short"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"


async def test_login_wrong_password_401(app_client) -> None:
    await signup_user(
        app_client, email="alice@example.com", username="alice"
    )
    r = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrong"},
    )
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHORIZED"


async def test_login_unknown_email_401(app_client) -> None:
    r = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "password123"},
    )
    assert r.status_code == 401


async def test_me_without_token_401(app_client) -> None:
    r = await app_client.get("/api/v1/me")
    # OAuth2PasswordBearer 가 자동 401 (auto_error=True 기본) — HTTPException 핸들러로 envelope
    assert r.status_code == 401


async def test_me_invalid_token_401(app_client) -> None:
    r = await app_client.get(
        "/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHORIZED"


async def test_token_returned_correctly(app_client) -> None:
    await signup_user(
        app_client, email="charlie@example.com", username="charlie"
    )
    token = await login_user(app_client, email="charlie@example.com")
    assert isinstance(token, str)
    assert len(token) > 20  # JWT 는 길다


async def test_request_id_header_echoed(app_client) -> None:
    r = await app_client.get("/healthz")
    assert "X-Request-ID" in r.headers or "x-request-id" in r.headers
