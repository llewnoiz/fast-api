"""직접 만든 _간단한_ Redis 기반 Rate Limiter.

알고리즘: **fixed window counter** (가장 단순).
    1. INCR 키
    2. 첫 호출이면 EXPIRE 설정 (윈도 시작)
    3. 카운터가 limit 초과면 429
    4. 윈도 끝나면 키 자동 만료 → 카운터 리셋

비교:
    Spring Cloud Gateway:  RequestRateLimiter (Redis, fixed window 또는 token bucket)
    NestJS:                ThrottlerGuard (in-memory 기본, Redis 백엔드 가능)
    AWS WAF:               rate-based rule

참고 — fixed window 의 _경계 효과_ 함정:
    윈도 끝-시작 사이 1초에 limit×2 가능 → 더 정확하려면 sliding window log / token bucket.
    학습/일반 용도엔 fixed window 충분.

대안 라이브러리: `slowapi`, `limits` (둘 다 학습 후 채택 가능).
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

KEY_PREFIX = "rate:"


class RateLimiter:
    """Depends 로 주입하는 callable.

    예: dependencies=[Depends(RateLimiter(times=3, seconds=5))]
    """

    def __init__(self, *, times: int, seconds: int) -> None:
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        redis: Redis = request.app.state.redis
        # 식별자: IP + 라우트 경로. user 기반은 JWT 주입 후 sub 사용.
        ident = (request.client.host if request.client else "unknown") + ":" + request.url.path
        key = f"{KEY_PREFIX}{ident}"

        # atomic 카운터 + 첫 호출에 TTL 설정 (pipeline 으로 묶어서 race 줄임)
        async with redis.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, self.seconds, nx=True)   # _아직 TTL 없을 때만_ 설정
            results = await pipe.execute()
        count = int(results[0])

        if count > self.times:
            ttl = await redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(max(ttl, 1))},
            )
