"""FastAPI 앱 — Redis 클라이언트 lifespan + cache / lock / rate limit 라우트.

Rate limit:
    fastapi-limiter 가 _Lua 스크립트_ 로 Redis 에 카운터 atomic 처리.
    `Depends(RateLimiter(times=N, seconds=T))` 한 줄로 라우트 보호.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from redis.asyncio import Redis

from cacheapp.cache import Cache
from cacheapp.lock import distributed_lock
from cacheapp.ratelimit import RateLimiter
from cacheapp.settings import get_settings

# ============================================================================
# lifespan — Redis 클라이언트 _하나_ 만들고 fastapi-limiter 초기화
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    app.state.redis = redis
    app.state.cache = Cache(redis, prefix=settings.cache_prefix, default_ttl=settings.cache_default_ttl)

    try:
        yield
    finally:
        await redis.aclose()


# ============================================================================
# 의존성
# ============================================================================


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


# ============================================================================
# 가짜 _느린 외부 API_ — cache-aside 효과 보여줄 데모용
# ============================================================================


_HIT_COUNT = {"slow_api": 0}


async def slow_external_api(item_id: int) -> dict[str, int | str]:
    """진짜라면 외부 HTTP 호출. 200ms 가짜 지연."""
    _HIT_COUNT["slow_api"] += 1
    await asyncio.sleep(0.2)
    return {"id": item_id, "name": f"item-{item_id}", "fetched_at": int(time.time())}


# ============================================================================
# FastAPI 앱
# ============================================================================


def create_app() -> FastAPI:
    app = FastAPI(title="redis-ratelimit", version="0.1.0", lifespan=lifespan)

    # ---------- cache-aside 데모 ----------
    @app.get("/items/{item_id}")
    async def get_item(
        item_id: int,
        cache: Annotated[Cache, Depends(get_cache)],
    ) -> dict[str, int | str]:
        # 첫 호출: 200ms (외부 호출), 이후: <1ms (캐시)
        return await cache.get_or_set(
            f"item:{item_id}",
            loader=lambda: slow_external_api(item_id),
            ttl=10,
        )

    @app.post("/items/{item_id}/invalidate", status_code=204)
    async def invalidate(
        item_id: int,
        cache: Annotated[Cache, Depends(get_cache)],
    ) -> None:
        await cache.invalidate(f"item:{item_id}")

    @app.get("/_stats/external_hits")
    async def stats() -> dict[str, int]:
        return {"slow_api_calls": _HIT_COUNT["slow_api"]}

    # ---------- 분산 락 데모 ----------
    @app.post("/orders/{order_id}/process")
    async def process_order(
        order_id: int,
        redis: Annotated[Redis, Depends(get_redis)],
    ) -> dict[str, str]:
        # 같은 order 의 _동시 처리_ 차단
        async with distributed_lock(redis, f"order:{order_id}", timeout=5.0, blocking_timeout=0.1) as got:
            if not got:
                raise HTTPException(status_code=429, detail="다른 요청 처리 중")
            await asyncio.sleep(0.3)  # 가짜 결제 처리
            return {"order_id": str(order_id), "status": "processed"}

    # ---------- Rate Limit 데모 ----------
    # 5초 안에 3번 까지 — IP 기반 (기본). user 기반은 identifier 커스텀.
    @app.get(
        "/limited",
        dependencies=[Depends(RateLimiter(times=3, seconds=5))],
    )
    async def limited() -> dict[str, str]:
        return {"ok": "true"}

    return app


app = create_app()
