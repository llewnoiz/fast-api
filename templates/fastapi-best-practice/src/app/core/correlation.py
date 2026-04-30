"""Correlation-ID 미들웨어 — 매 요청에 X-Request-ID + structlog contextvars.

로그가 _요청별_ 묶임 → Loki / ELK 에서 _하나의 요청 흐름_ 추적 가능.
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
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path)
        try:
            response = await call_next(request)
        finally:
            # 누수 방지 — 다음 요청에 _이 요청의 컨텍스트_ 새지 않도록
            structlog.contextvars.clear_contextvars()
        response.headers[REQUEST_ID_HEADER] = rid
        return response


def install_correlation_middleware(app: FastAPI) -> None:
    app.add_middleware(CorrelationIdMiddleware)
