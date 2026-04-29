"""07 — 앱 조립.

04 와 다른 점:
    1. 응답 envelope (ApiEnvelope[T])
    2. 전역 예외 핸들러 (도메인/검증/HTTP/미처리)
    3. /v1, /v2 라우터 분리 + Deprecation 헤더
    4. OpenAPI examples / responses 풍부화
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from errver.api import v1, v2
from errver.handlers import install_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="request-error-version",
        version="0.2.0",
        description=(
            "07 단계 학습용 — 응답 envelope + 전역 에러 핸들러 + API 버전 관리.\n\n"
            "**v1 은 deprecated**. 새 클라이언트는 v2 사용."
        ),
        lifespan=lifespan,
    )

    install_exception_handlers(app)

    for r in v1.routers:
        app.include_router(r)
    for r in v2.routers:
        app.include_router(r)

    return app


app = create_app()
