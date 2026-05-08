"""FastAPI 앱 — create_app() factory + lifespan.

lifespan 에서 _하나_ 의 인스턴스로:
    - SQLAlchemy AsyncEngine + sessionmaker (풀 튜닝 적용)
    - Redis 클라이언트 + ItemCache
    - Settings

미들웨어 _순서_ (역순 실행):
    1. SecurityHeadersMiddleware (가장 바깥 — 모든 응답에 헤더)
    2. CORSMiddleware (preflight 처리)
    3. CorrelationIdMiddleware (요청 ID + structlog 컨텍스트)
    4. (Rate limit 은 dependency 로 — 미들웨어 X)

라우터:
    - `app.api.v1.router` — `/api/v1/*` 도메인 라우터 통합
    - `app.api.health` — `/healthz` (liveness) + `/readyz` (readiness)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.cache.client import ItemCache
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.db.session import make_engine, make_sessionmaker
from app.middleware.correlation import install_correlation_middleware
from app.middleware.handlers import install_exception_handlers
from app.middleware.security_headers import install_security_headers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(env=settings.env, log_level=settings.log_level)
    log = structlog.get_logger()

    engine = make_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_timeout=settings.db_pool_timeout,
    )
    sm = make_sessionmaker(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = sm
    app.state.redis = redis
    app.state.cache = ItemCache(redis, ttl=settings.cache_ttl_seconds)

    log.info("app.starting", env=settings.env)
    try:
        yield
    finally:
        log.info("app.stopping")
        await engine.dispose()
        await redis.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="app",
        version="0.4.0",
        description="FastAPI best-practice starter",
        lifespan=lifespan,
    )

    # ── 미들웨어 (역순 실행 — 마지막 등록이 _가장 안쪽_) ──
    install_correlation_middleware(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    install_security_headers(
        app, is_prod=settings.is_prod, csp_policy=settings.csp_policy
    )

    install_exception_handlers(app)

    app.include_router(v1_router)
    app.include_router(health_router)

    return app


app = create_app()
