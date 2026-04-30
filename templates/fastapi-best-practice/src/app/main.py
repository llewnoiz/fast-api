"""FastAPI 앱 — create_app() factory + lifespan.

lifespan 에서 _하나_ 의 인스턴스로:
    - SQLAlchemy AsyncEngine + sessionmaker
    - Redis 클라이언트 + ItemCache
    - Settings

미들웨어 + 핸들러 = `app.core.{correlation, handlers, logging}` 모듈로 분리.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.v1 import router as v1_router
from app.cache.client import ItemCache
from app.core.correlation import install_correlation_middleware
from app.core.handlers import install_exception_handlers
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.db.session import make_engine, make_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(env=settings.env, log_level=settings.log_level)
    log = structlog.get_logger()

    engine = make_engine(settings.database_url)
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
    app = FastAPI(
        title="app",
        version="0.1.0",
        description="FastAPI best-practice starter",
        lifespan=lifespan,
    )

    install_correlation_middleware(app)
    install_exception_handlers(app)

    app.include_router(v1_router)

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        """Docker HEALTHCHECK 용 ── 단순 200, envelope 미적용."""
        return {"status": "ok"}

    return app


app = create_app()
