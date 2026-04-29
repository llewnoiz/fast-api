"""09 — 로그인 / JWT / 가드 / RBAC 검증."""

from __future__ import annotations

import pytest
from authapp.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from httpx import AsyncClient


# ---------- 단위 — 비밀번호 해싱 ----------
class TestPasswordHashing:
    def test_hash_is_not_plain(self) -> None:
        h = hash_password("secret")
        assert h != "secret"
        assert h.startswith("$2b$")        # bcrypt 헤더

    def test_verify_correct(self) -> None:
        h = hash_password("secret")
        assert verify_password("secret", h) is True

    def test_verify_wrong(self) -> None:
        h = hash_password("secret")
        assert verify_password("WRONG", h) is False

    def test_same_password_different_hashes(self) -> None:
        # salt 자동 → 같은 비번도 매번 다른 해시
        assert hash_password("x") != hash_password("x")


# ---------- 단위 — JWT ----------
class TestJWT:
    def test_encode_decode_roundtrip(self) -> None:
        token = create_access_token(subject="alice", roles=["admin"])
        payload = decode_access_token(token)
        assert payload["sub"] == "alice"
        assert payload["roles"] == ["admin"]
        assert "exp" in payload and "iat" in payload

    def test_invalid_token_raises(self) -> None:
        import jwt as pyjwt  # noqa: PLC0415

        with pytest.raises(pyjwt.PyJWTError):
            decode_access_token("not.a.real.jwt")


# ---------- 통합 — 라우트 ----------
class TestLogin:
    async def test_login_returns_bearer_token(self, client: AsyncClient) -> None:
        r = await client.post("/auth/token", data={"username": "alice", "password": "alice123"})
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str) and len(body["access_token"]) > 20

    async def test_wrong_password_401(self, client: AsyncClient) -> None:
        r = await client.post("/auth/token", data={"username": "alice", "password": "WRONG"})
        assert r.status_code == 401

    async def test_unknown_user_401(self, client: AsyncClient) -> None:
        # 존재 _여부_ 노출 X — 같은 메시지
        r = await client.post("/auth/token", data={"username": "ghost", "password": "x"})
        assert r.status_code == 401

    async def test_missing_form_fields_422(self, client: AsyncClient) -> None:
        # OAuth2PasswordRequestForm 의 username/password 누락 → Pydantic/FastAPI 422
        r = await client.post("/auth/token", data={"username": "alice"})
        assert r.status_code == 422


class TestMe:
    async def test_unauthorized_without_token(self, client: AsyncClient) -> None:
        r = await client.get("/me")
        assert r.status_code == 401

    async def test_authorized_with_token(self, client: AsyncClient, alice_token: str) -> None:
        r = await client.get("/me", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "alice"
        assert "admin" in body["roles"]
        # 절대 password_hash 노출 X
        assert "password_hash" not in body

    async def test_invalid_token_401(self, client: AsyncClient) -> None:
        r = await client.get("/me", headers={"Authorization": "Bearer fake.jwt.token"})
        assert r.status_code == 401


class TestRBAC:
    async def test_admin_can_access_admin_secret(
        self, client: AsyncClient, alice_token: str
    ) -> None:
        r = await client.get("/admin/secret", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 200
        assert r.json()["who"] == "alice"

    async def test_non_admin_gets_403(self, client: AsyncClient, bob_token: str) -> None:
        # bob 은 user 만, admin 아님
        r = await client.get("/admin/secret", headers={"Authorization": f"Bearer {bob_token}"})
        assert r.status_code == 403

    async def test_no_token_401_not_403(self, client: AsyncClient) -> None:
        # 토큰 없을 땐 403 이 아니라 401 (인증 우선)
        r = await client.get("/admin/secret")
        assert r.status_code == 401

    async def test_admin_or_auditor_allowed(
        self, client: AsyncClient, carol_token: str, alice_token: str, bob_token: str
    ) -> None:
        # carol = auditor → 200
        r = await client.get("/audit/log", headers={"Authorization": f"Bearer {carol_token}"})
        assert r.status_code == 200

        # alice = admin → 200 (admin 또는 auditor 둘 중 하나면 OK)
        r = await client.get("/audit/log", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 200

        # bob = user 만 → 403
        r = await client.get("/audit/log", headers={"Authorization": f"Bearer {bob_token}"})
        assert r.status_code == 403
