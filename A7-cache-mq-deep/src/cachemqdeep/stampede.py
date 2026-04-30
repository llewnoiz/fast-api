"""캐시 Stampede 방지 (Thundering Herd).

문제 시나리오:
    인기 키의 TTL 이 _만료된 직후_ 동시에 도착한 N 개 요청이 모두 _캐시 미스_ →
    같은 비싼 계산 / DB 쿼리를 N 번 동시 실행 → DB 폭발 + 응답 지연.

해법 3가지 (조합 가능):

1. **Lock (mutex)** ── 가장 직관
    가장 먼저 도착한 _하나만_ 재계산. 나머지는 락 풀릴 때까지 대기 후 캐시 hit.
    문제: 대기 시간이 latency 에 더해짐. lock holder 가 죽으면 timeout 까지 무방비.

2. **Probabilistic Early Refresh (PER)** ── _만료 전_ 갱신
    TTL 이 끝나가는 _확률적_ 시점에 _하나의 요청만_ 재계산을 자발적으로 수행.
    수학: `expire_at - now < beta * delta_re_compute * ln(rand())` 가 True 면 재계산.
    참고: 2015 논문 _XFetch_. RedisLabs RedLock 페이지에 자세히.

3. **Stale-While-Revalidate (SWR)** ── _만료 후에도_ 잠시 옛 값 반환
    HTTP `Cache-Control: stale-while-revalidate=60` 의 _서버측_ 버전.
    _옛 값을 반환_ 하면서 백그라운드로 재계산.

본 모듈은:
    - `get_or_set_with_lock(...)` — 1번 (가장 단순, 학습용)
    - `get_or_set_xfetch(...)` — 2번 (PER — 락 없이 _확률적_ 분산)

비교:
    Spring `@Cacheable(sync = true)` — 1번 (lock-based) 자동 적용
    Caffeine `Caffeine.refreshAfterWrite(...)` — 3번 (SWR) 우아한 추상화
    Cloudflare/Fastly `stale-while-revalidate` — HTTP 표준 SWR
"""

from __future__ import annotations

import asyncio
import math
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

import orjson
from redis.asyncio import Redis


async def get_or_set_with_lock(
    redis: Redis,
    key: str,
    loader: Callable[[], Awaitable[Any]],
    *,
    ttl: int,
    lock_ttl: int = 5,
    poll_interval: float = 0.05,
) -> Any:
    """캐시 미스 시 _하나의 요청만_ loader 호출. 나머지는 짧게 폴링 후 hit.

    동작:
        1) GET key → 있으면 즉시 반환
        2) SET NX `lock:{key}` (lock_ttl) → 획득자만 loader 실행 후 SET key
        3) 락 못 잡은 요청은 _락 사라질 때까지_ poll → 다시 GET key
    """
    cached = await redis.get(key)
    if cached is not None:
        return orjson.loads(cached)

    lock_key = f"lock:{key}"
    got_lock = await redis.set(lock_key, "1", nx=True, ex=lock_ttl)
    if got_lock:
        try:
            value = await loader()
            await redis.set(key, orjson.dumps(value), ex=ttl)
            return value
        finally:
            await redis.delete(lock_key)

    # 락 못 잡음 — 다른 워커가 채우는 중. 짧게 폴링.
    deadline = time.monotonic() + lock_ttl
    while time.monotonic() < deadline:
        cached = await redis.get(key)
        if cached is not None:
            return orjson.loads(cached)
        await asyncio.sleep(poll_interval)
    # timeout fallback — _자기 자신이_ 계산. 안전망.
    return await loader()


async def get_or_set_xfetch(
    redis: Redis,
    key: str,
    loader: Callable[[], Awaitable[Any]],
    *,
    ttl: int,
    beta: float = 1.0,
) -> Any:
    """**XFetch** — Probabilistic Early Refresh.

    캐시에 값 + _직전 계산 시간_ (delta) 을 함께 저장. 매 GET 마다 다음 식 평가:

        rand() in (0, 1)  ─ 균등 분포
        expiry_in_seconds = TTL_remaining
        if delta * beta * (-ln(rand())) >= expiry_in_seconds:
            재계산

    delta 는 _직전 계산이 얼마나 걸렸는지_. 비싼 작업일 수록 _일찍_ 재계산할 확률 ↑.
    beta 는 _공격성_. 1.0 이 표준, 더 키우면 더 일찍.

    효과: 락 없이도 _만료 직전_ 에 _아주 적은_ 요청만 재계산. 나머지는 캐시 hit.
    """
    raw = await redis.get(key)
    if raw is not None:
        entry = orjson.loads(raw)
        delta = entry["delta"]
        expire_at = entry["expire_at"]
        now = time.time()
        remaining = expire_at - now
        # XFetch 식
        if remaining > 0 and delta * beta * (-math.log(random.random())) < remaining:
            return entry["value"]
        # 만료 임박 (또는 이미 만료) — 재계산

    started = time.monotonic()
    value = await loader()
    delta = time.monotonic() - started
    payload = {"value": value, "delta": delta, "expire_at": time.time() + ttl}
    await redis.set(key, orjson.dumps(payload), ex=ttl)
    return value
