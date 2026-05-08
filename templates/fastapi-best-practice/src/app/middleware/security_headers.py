"""Security 헤더 미들웨어 — 모든 응답에 _운영급 보안 헤더_ 자동 부착.

OWASP Secure Headers Project 권장:
    - `Strict-Transport-Security` ── HTTPS 강제 (dev 에선 _비활성_, prod 만)
    - `X-Content-Type-Options: nosniff` ── MIME 스니핑 방지 (CWE-430)
    - `X-Frame-Options: DENY` ── clickjacking 방지 (CWE-1021)
    - `Referrer-Policy: strict-origin-when-cross-origin` ── referrer 누수 방지
    - `Content-Security-Policy` ── XSS 완화 (CWE-79)
    - `Permissions-Policy` ── 브라우저 기능 제한 (geolocation 등)

운영 주의:
    - CSP 는 _프론트엔드 자산_ 에 따라 다름. 본 default 는 _API 전용_ (default-src 'self').
      SPA 호스팅하면 `script-src` / `connect-src` 등 추가.
    - HSTS `max-age` 는 점진적 증가 권장 (300 → 86400 → 31536000). 한 번 켜면 _롤백 어려움_.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """모든 응답에 보안 헤더 추가."""

    def __init__(
        self,
        app,  # noqa: ANN001
        *,
        is_prod: bool,
        csp_policy: str,
    ) -> None:
        super().__init__(app)
        self.is_prod = is_prod
        self.csp_policy = csp_policy

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        # 항상 적용
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault("Content-Security-Policy", self.csp_policy)
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )

        # HSTS — _운영_ (HTTPS) 만. dev 에서 켜면 localhost 도 HTTPS 강제 → 디버깅 함정.
        if self.is_prod:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains; preload",
            )

        return response


def install_security_headers(app: FastAPI, *, is_prod: bool, csp_policy: str) -> None:
    app.add_middleware(
        SecurityHeadersMiddleware, is_prod=is_prod, csp_policy=csp_policy
    )
