"""correlation-id 미들웨어 + structlog contextvars 바인딩.

흐름:
    1. 요청 헤더 X-Request-ID 가 있으면 _그대로_ 사용 (분산 시스템 추적)
    2. 없으면 _새 UUID_ 발급
    3. structlog 의 contextvars 에 바인딩 → _이 요청의 모든 로그에 자동 첨부_
    4. 응답 헤더에도 X-Request-ID 포함 → 클라이언트가 추적 가능
    5. (12 의 OTel 도 W3C `traceparent` 헤더 자동 처리)

비교:
    Spring Sleuth/Brave: MDC 에 traceId/spanId 자동
    NestJS:              cls-rs (AsyncLocalStorage)
    Go:                  context.Context
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 1) 요청 헤더에서 가져오거나 발급
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex

        # 2) 요청별 컨텍스트 — 이 요청 안의 _모든_ 로그에 자동 첨부
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path)

        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()

        # 3) 응답 헤더에도 포함
        response.headers[REQUEST_ID_HEADER] = rid
        return response


def install_correlation_middleware(app: FastAPI) -> None:
    app.add_middleware(CorrelationIdMiddleware)
