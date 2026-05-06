"""Refresh token 플로우 — login → refresh → rotation → revoke / logout-all."""

from __future__ import annotations

import pytest

from tests.conftest import signup_user

pytestmark = pytest.mark.integration


async def test_login_returns_access_and_refresh(app_client) -> None:
    await signup_user(app_client, email="alice@example.com", username="alice")
    r = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_refresh_rotates_tokens(app_client) -> None:
    """refresh 1번 → 새 access + 새 refresh. 옛 refresh 는 무효."""
    await signup_user(app_client, email="alice@example.com", username="alice")
    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    old_pair = login.json()["data"]

    # refresh 1번
    r = await app_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_pair["refresh_token"]}
    )
    assert r.status_code == 200
    new_pair = r.json()["data"]
    assert new_pair["access_token"] != old_pair["access_token"]
    assert new_pair["refresh_token"] != old_pair["refresh_token"]

    # 새 access 로 /me 호출
    me = await app_client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {new_pair['access_token']}"}
    )
    assert me.status_code == 200


async def test_old_refresh_revoked_after_rotation(app_client) -> None:
    """rotation 후 옛 refresh _재사용_ 시도 → 401 (token reuse 탐지)."""
    await signup_user(app_client, email="alice@example.com", username="alice")
    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    old_refresh = login.json()["data"]["refresh_token"]

    # 1차 rotation
    await app_client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

    # 옛 refresh 재사용 → 401
    r = await app_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHORIZED"


async def test_refresh_with_access_token_rejected(app_client) -> None:
    """access token 으로 refresh 시도 → type 검증 실패."""
    await signup_user(app_client, email="alice@example.com", username="alice")
    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    access = login.json()["data"]["access_token"]

    r = await app_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access}
    )
    assert r.status_code == 401


async def test_logout_revokes_current_refresh(app_client) -> None:
    await signup_user(app_client, email="alice@example.com", username="alice")
    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    refresh_t = login.json()["data"]["refresh_token"]

    # logout
    r = await app_client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_t}
    )
    assert r.status_code == 200

    # 같은 refresh 로 /auth/refresh → 401
    after = await app_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_t}
    )
    assert after.status_code == 401


async def test_logout_idempotent(app_client) -> None:
    """logout 두 번 호출해도 OK (idempotent)."""
    await signup_user(app_client, email="alice@example.com", username="alice")
    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    refresh_t = login.json()["data"]["refresh_token"]

    r1 = await app_client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_t}
    )
    r2 = await app_client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_t}
    )
    assert r1.status_code == r2.status_code == 200


async def test_logout_all_revokes_every_session(app_client) -> None:
    """alice 가 _두 디바이스_ 로그인 → logout-all → 둘 다 무효."""
    await signup_user(app_client, email="alice@example.com", username="alice")
    login_data = {"email": "alice@example.com", "password": "password123"}
    a = await app_client.post("/api/v1/auth/login", json=login_data)
    b = await app_client.post("/api/v1/auth/login", json=login_data)
    pair_a = a.json()["data"]
    pair_b = b.json()["data"]

    # access 로 logout-all
    r = await app_client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {pair_a['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["revoked"] >= 2

    # 둘 다 refresh 무효
    for pair in (pair_a, pair_b):
        rr = await app_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )
        assert rr.status_code == 401


async def test_invalid_refresh_token_rejected(app_client) -> None:
    r = await app_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"}
    )
    assert r.status_code == 401
