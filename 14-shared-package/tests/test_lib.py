"""fastapi-common 자체 단위 테스트 — 외부 인프라 의존 X."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from fastapi_common import (
    REQUEST_ID_HEADER,
    ApiEnvelope,
    DomainError,
    ErrorCode,
    ResilientClient,
    __version__,
    install_correlation_middleware,
    install_exception_handlers,
    make_breaker_factory,
    success,
)
from httpx import ASGITransport, AsyncClient


# ---------- 공개 API surface 안정성 ----------
class TestPublicSurface:
    def test_version_is_semver(self) -> None:
        # x.y.z
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


# ---------- envelope ----------
class TestEnvelope:
    def test_success_helper(self) -> None:
        e = success({"id": 1}, "ok")
        assert e.code == "OK"
        assert e.data == {"id": 1}

    def test_generic_typing(self) -> None:
        # PEP 695 제네릭 — 런타임엔 BaseModel 동작
        e = ApiEnvelope[dict](code="X", message="m", data={"k": "v"})
        assert e.model_dump() == {"code": "X", "message": "m", "data": {"k": "v"}}


# ---------- errors ----------
class TestErrors:
    def test_error_code_values(self) -> None:
        # 공개 API — 값 _절대_ 변경 금지
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
        assert ErrorCode.VALIDATION.value == "VALIDATION_ERROR"

    def test_domain_error_with_enum(self) -> None:
        e = DomainError(code=ErrorCode.NOT_FOUND, message="missing", status=404)
        assert e.code == "NOT_FOUND"
        assert e.status == 404

    def test_domain_error_with_string_code(self) -> None:
        e = DomainError(code="CUSTOM_DOMAIN", message="x", status=409)
        assert e.code == "CUSTOM_DOMAIN"


# ---------- 통합: 미니 앱 — 라이브러리 _사용 측_ 시나리오 ----------
class TestIntegrationWithFastAPI:
    """라이브러리를 _실제_ FastAPI 앱에 끼워서 동작 검증."""

    def _build_app(self) -> FastAPI:
        app = FastAPI()
        install_correlation_middleware(app)
        install_exception_handlers(app)

        @app.get("/ok")
        async def ok() -> ApiEnvelope[dict]:
            return success({"hello": "world"})

        @app.get("/notfound")
        async def notfound() -> None:
            raise DomainError(code=ErrorCode.NOT_FOUND, message="missing", status=404)

        return app

    @pytest.mark.asyncio
    async def test_envelope_response(self) -> None:
        app = self._build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/ok")
            assert r.status_code == 200
            body = r.json()
            assert body["code"] == "OK"
            assert body["data"] == {"hello": "world"}
            # correlation-id 헤더 자동
            assert r.headers.get(REQUEST_ID_HEADER.lower()) is not None

    @pytest.mark.asyncio
    async def test_domain_error_to_envelope(self) -> None:
        app = self._build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/notfound")
            assert r.status_code == 404
            body = r.json()
            assert body["code"] == "NOT_FOUND"
            assert body["message"] == "missing"


# ---------- ResilientClient — MockTransport ----------
class TestResilientClient:
    @pytest.mark.asyncio
    async def test_retry_on_5xx_then_success(self) -> None:
        calls = {"n": 0}

        async def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(500 if calls["n"] < 2 else 200, json={"v": calls["n"]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            rc = ResilientClient(client, make_breaker_factory(threshold=10), retry_attempts=3)
            result = await rc.get_json("https://x/y")
            assert result == {"v": 2}
