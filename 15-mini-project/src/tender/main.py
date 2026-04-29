"""tender 앱 — FastAPI 조립.

lifespan 에서 _하나_ 의 인스턴스로:
    - SQLAlchemy AsyncEngine + sessionmaker (10)
    - Redis 클라이언트 + OrderCache (11)
    - Settings (04)

미들웨어 + 핸들러 = fastapi-common (14) 활용:
    - install_correlation_middleware (12)
    - install_exception_handlers (07)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi_common import (
    configure_logging,
    install_correlation_middleware,
    install_exception_handlers,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from tender.api import auth, v1, v2
from tender.cache import OrderCache
from tender.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(env=settings.env, log_level="INFO")
    log = structlog.get_logger()

    # DB
    engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sm = async_sessionmaker(engine, expire_on_commit=False)

    # Redis
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = sm
    app.state.redis = redis
    app.state.cache = OrderCache(redis, ttl=settings.cache_ttl_seconds)

    log.info("tender.starting", env=settings.env)
    try:
        yield
    finally:
        log.info("tender.stopping")
        await engine.dispose()
        await redis.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="tender",
        version="0.1.0",
        description="15 단계 — 통합 미니 프로젝트. 04~14 모두 결합.",
        lifespan=lifespan,
    )

    # fastapi-common (14) 활용
    install_correlation_middleware(app)
    install_exception_handlers(app)

    # 라우터
    app.include_router(auth.router)
    app.include_router(v1.router)
    app.include_router(v2.router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
