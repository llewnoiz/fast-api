"""미들웨어 — 매 요청마다 Accept-Language → contextvars 의 locale 설정.

호출 순서:
    1. 미들웨어가 헤더 파싱 → `set_locale(...)`
    2. 라우트 / 의존성이 `gettext("key")` 호출 → `get_locale()` 자동 사용
    3. 응답 생성

또 다른 locale 결정 방식:
    - URL prefix (`/ko/...`, `/en/...`) — SEO 친화 (검색엔진이 _언어별 URL_ 좋아함)
    - 쿠키 (`lang=ko`) — 사용자 선택 영구화
    - 사용자 프로필 — 로그인 시 DB 값
    - JWT claim ── 토큰에 `locale` 클레임

운영 우선순위 (보통):
    URL prefix > 쿠키 > 사용자 프로필 > Accept-Language > default
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from i18napp.locale import negotiate_locale, set_locale


class LocaleMiddleware(BaseHTTPMiddleware):
    """`Accept-Language` 헤더 → contextvars locale 설정 + `Content-Language` 응답 헤더."""

    def __init__(self, app, *, supported: list[str], default: str = "en") -> None:  # noqa: ANN001
        super().__init__(app)
        self.supported = supported
        self.default = default

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 1) 쿠키 우선 (사용자 선택 영구화)
        cookie_locale = request.cookies.get("locale")
        if cookie_locale and cookie_locale in self.supported:
            locale = cookie_locale
        else:
            # 2) Accept-Language 헤더
            locale = negotiate_locale(
                request.headers.get("accept-language"),
                supported=self.supported,
                default=self.default,
            )
        set_locale(locale)
        response = await call_next(request)
        response.headers["content-language"] = locale
        return response
