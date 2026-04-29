"""FastAPI 앱 — 12 단계 통합 데모.

라우트:
    GET /relay?url=...       외부 URL 호출 (재시도 + 회로 차단기)
    GET /flaky               의도적으로 가끔 실패 (재시도 데모용)
    GET /healthz             단순 OK
    GET /metrics             Prometheus 자동 노출
"""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request

from obsapp.correlation import install_correlation_middleware
from obsapp.http_client import ResilientClient, make_breaker_factory
from obsapp.observability import setup_otel, setup_prometheus
from obsapp.settings import get_settings

log = structlog.get_logger()


# ============================================================================
# lifespan — httpx.AsyncClient + 회로 차단기 팩토리 _하나_
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    httpx_client = httpx.AsyncClient(timeout=settings.http_timeout_s)
    breakers = make_breaker_factory(
        threshold=settings.breaker_threshold,
        recovery_s=settings.breaker_recovery_s,
    )
    app.state.resilient = ResilientClient(httpx_client, breakers, retry_attempts=settings.retry_attempts)

    log.info("app.starting")
    try:
        yield
    finally:
        await httpx_client.aclose()
        log.info("app.stopping")


# ============================================================================
# 의존성
# ============================================================================


def get_resilient(request: Request) -> ResilientClient:
    return request.app.state.resilient


# ============================================================================
# FastAPI 앱
# ============================================================================


def create_app() -> FastAPI:
    app = FastAPI(title="service-comm-observability", version="0.1.0", lifespan=lifespan)

    # 1) correlation-id 가 _가장 먼저_ 들어가야 다른 미들웨어/로그에 컨텍스트 적용됨
    install_correlation_middleware(app)

    # 2) Prometheus — /metrics 자동
    setup_prometheus(app)

    # 3) OTel — FastAPIInstrumentor 가 _후속_ 미들웨어로 등록 (적합)
    settings = get_settings()
    setup_otel(app, settings)

    # ---------- 라우트 ----------

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/relay")
    async def relay(
        url: str,
        client: Annotated[ResilientClient, Depends(get_resilient)],
    ) -> Any:
        """외부 URL 그대로 가져와 반환. 재시도 + 회로 차단기 적용."""
        try:
            return await client.get_json(url)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"upstream error: {e!s}") from e

    @app.get("/flaky")
    async def flaky() -> dict[str, str]:
        """50% 확률로 500. tests 에서 mock transport 로 _결정적_ 으로 재시도 검증."""
        if random.random() < 0.5:
            log.warning("flaky.fail")
            raise HTTPException(status_code=500, detail="random failure")
        return {"status": "ok"}

    return app


app = create_app()
