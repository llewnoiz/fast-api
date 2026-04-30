"""A5 통합 — TOTP / API key / 보안 헤더 / SSRF 방어 라우트."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from secapp import api_key as ak
from secapp import totp
from secapp.owasp_examples import (
    fetch_with_ssrf_guard,
    secure_headers,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 학습용 — API key 시드
    ak.seed(["ak_test_key_123", "ak_test_key_456"])
    app.state.httpx = httpx.AsyncClient()
    try:
        yield
    finally:
        await app.state.httpx.aclose()


# ============================================================================
# 보안 헤더 미들웨어
# ============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: ANN001, ANN201
        response: Response = await call_next(request)
        for k, v in secure_headers().items():
            response.headers[k] = v
        return response


# ============================================================================
# 스키마
# ============================================================================


class TotpEnrollResponse(BaseModel):
    secret: str
    otpauth_uri: str


class TotpVerifyRequest(BaseModel):
    secret: str
    code: str


# ============================================================================
# 앱
# ============================================================================


def create_app() -> FastAPI:
    app = FastAPI(title="security-deep", version="0.1.0", lifespan=lifespan)
    app.add_middleware(SecurityHeadersMiddleware)

    # ---------- TOTP ----------
    @app.post("/totp/enroll", response_model=TotpEnrollResponse)
    async def totp_enroll(account: str = "alice@example.com") -> TotpEnrollResponse:
        secret = totp.generate_secret()
        return TotpEnrollResponse(
            secret=secret,
            otpauth_uri=totp.provisioning_uri(secret=secret, account=account),
        )

    @app.post("/totp/verify")
    async def totp_verify(payload: TotpVerifyRequest) -> dict[str, bool]:
        return {"valid": totp.verify(payload.secret, payload.code)}

    # ---------- API key ----------
    @app.get("/internal/data", dependencies=[Depends(ak.require_api_key)])
    async def internal_data() -> dict[str, str]:
        """API key 없으면 401."""
        return {"data": "secret-internal"}

    # ---------- SSRF 방어 외부 호출 ----------
    @app.get("/relay")
    async def relay(request: Request, url: str) -> dict[str, object]:
        """사용자 입력 URL — _안전 검증_ 후 호출."""
        try:
            client: httpx.AsyncClient = request.app.state.httpx
            resp = await fetch_with_ssrf_guard(client, url)
            return {"status": resp.status_code, "snippet": resp.text[:200]}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    return app


app = create_app()
