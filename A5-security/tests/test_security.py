"""A5 — 보안 단위 + 통합 테스트."""

from __future__ import annotations

import pyotp
import pytest
from httpx import AsyncClient
from secapp import api_key as ak
from secapp import totp
from secapp.owasp_examples import is_private_host, safe_external_url


# ---------- TOTP ----------
class TestTOTP:
    def test_generate_secret_is_base32(self) -> None:
        secret = totp.generate_secret()
        # base32 — A-Z, 2-7, 보통 32자
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)
        assert len(secret) >= 16

    def test_verify_with_current_code(self) -> None:
        secret = totp.generate_secret()
        code = pyotp.TOTP(secret).now()
        assert totp.verify(secret, code) is True

    def test_verify_wrong_code(self) -> None:
        secret = totp.generate_secret()
        assert totp.verify(secret, "000000") is False

    def test_provisioning_uri_format(self) -> None:
        uri = totp.provisioning_uri(secret="ABCD2345" * 4, account="alice@example.com")
        assert uri.startswith("otpauth://totp/tender:alice")
        assert "secret=" in uri


# ---------- API key ----------
class TestApiKey:
    def test_generate_returns_raw_and_hash(self) -> None:
        raw, h = ak.generate_api_key()
        assert raw.startswith("ak_")
        assert len(h) == 64  # sha256 hex

    def test_hash_is_deterministic(self) -> None:
        raw, h1 = ak.generate_api_key()
        h2 = ak.hash_key(raw)
        assert h1 == h2

    async def test_api_key_required_401(self, app_client: AsyncClient) -> None:
        r = await app_client.get("/internal/data")
        assert r.status_code == 401

    async def test_api_key_invalid_401(self, app_client: AsyncClient) -> None:
        r = await app_client.get("/internal/data", headers={"X-API-Key": "wrong"})
        assert r.status_code == 401

    async def test_api_key_valid_200(self, app_client: AsyncClient) -> None:
        r = await app_client.get(
            "/internal/data", headers={"X-API-Key": "ak_test_key_123"}
        )
        assert r.status_code == 200
        assert r.json()["data"] == "secret-internal"


# ---------- SSRF 방어 ----------
class TestSSRF:
    @pytest.mark.parametrize(
        "host",
        ["127.0.0.1", "localhost", "10.0.0.1", "169.254.169.254", "192.168.1.1"],
    )
    def test_private_hosts_blocked(self, host: str) -> None:
        assert is_private_host(host)

    @pytest.mark.parametrize("host", ["8.8.8.8", "example.com", "1.1.1.1"])
    def test_public_hosts_allowed(self, host: str) -> None:
        assert not is_private_host(host)

    def test_safe_url_rejects_private(self) -> None:
        with pytest.raises(ValueError, match="private host"):
            safe_external_url("http://169.254.169.254/latest/meta-data/")

    def test_safe_url_rejects_file_scheme(self) -> None:
        with pytest.raises(ValueError, match="scheme"):
            safe_external_url("file:///etc/passwd")

    def test_safe_url_allowlist(self) -> None:
        # allowed_hosts 사용 시 — 화이트리스트 외 차단
        with pytest.raises(ValueError, match="allowlist"):
            safe_external_url("https://evil.com/x", allowed_hosts={"good.com"})
        # 화이트리스트 안은 통과
        assert safe_external_url(
            "https://good.com/x", allowed_hosts={"good.com"}
        ) == "https://good.com/x"


# ---------- 보안 헤더 ----------
class TestSecurityHeaders:
    async def test_response_has_secure_headers(self, app_client: AsyncClient) -> None:
        r = await app_client.post(
            "/totp/enroll", params={"account": "test@example.com"}
        )
        # 모든 응답에 보안 헤더 자동
        assert "strict-transport-security" in r.headers
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"


# ---------- TOTP 라우트 통합 ----------
class TestTotpEndpoints:
    async def test_enroll_then_verify(self, app_client: AsyncClient) -> None:
        # 1) enroll — secret + uri 발급
        r = await app_client.post("/totp/enroll", params={"account": "alice@example.com"})
        assert r.status_code == 200
        body = r.json()
        secret = body["secret"]
        assert body["otpauth_uri"].startswith("otpauth://totp/tender:alice")

        # 2) 현재 시간 코드 생성 → verify
        code = pyotp.TOTP(secret).now()
        r = await app_client.post("/totp/verify", json={"secret": secret, "code": code})
        assert r.status_code == 200
        assert r.json()["valid"] is True

    async def test_verify_wrong_code(self, app_client: AsyncClient) -> None:
        r = await app_client.post(
            "/totp/verify", json={"secret": "ABCDEFGHIJKLMNOP", "code": "000000"}
        )
        assert r.status_code == 200
        assert r.json()["valid"] is False
