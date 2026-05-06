"""Redis 기반 fixed-window Rate Limiter.

알고리즘 (fixed window counter):
    1. INCR 키
    2. 첫 호출이면 EXPIRE 설정 (윈도 시작)
    3. 카운터 > limit → 429 + Retry-After 헤더
    4. 윈도 끝나면 키 자동 만료

`fixed window` 함정:
    윈도 끝-시작 사이 _1초_ 에 limit×2 요청 가능. 더 정확하려면:
    - **sliding window log** (Redis ZSET 으로 timestamp 저장) — 더 정확, 메모리 ↑
    - **token bucket** (refill rate) — 가장 운영급, 구현 복잡

학습 / 일반 보호엔 fixed window _충분_. login brute-force 방지 등.

대안 라이브러리:
    - `slowapi` (Flask-Limiter 의 Starlette 포트) — 간편 데코레이터
    - `fastapi-limiter` — Redis backend, 단 PyPI 동명 패키지 주의 (long2ice 의 0.1.6 가 진짜)
    - `limits` — 라이브러리 자체, 백엔드 추상화

운영 추가 권장:
    - **CDN/WAF** (Cloudflare / AWS WAF) 가 _앱 도달 전_ rate limit. 본 모듈은 _세컨드 라인_.
    - 사용자별 (JWT sub) + IP 별 _이중 키_ 로 IPv6 회전 공격 대응.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

KEY_PREFIX = "rate:"


class RateLimiter:
    """`Depends(RateLimiter(key="login", settings_attr="rate_limit_login_per_min"))`.

    설계: `times` 를 _직접_ 받지 않고 `settings_attr` (Settings 의 필드명) 으로 _런타임_ 조회.
    이유: 환경변수 / 테스트 override 시 _instance 재생성 불필요_. 단일 dependency 가 매번 settings 봄.

    `key` ── 라우트 식별자 (login / write 등). 같은 IP 가 _여러 라우트_ 에 _독립_ 카운트.
    """

    def __init__(
        self, *, key: str, settings_attr: str, seconds: int = 60
    ) -> None:
        self.key = key
        self.settings_attr = settings_attr
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        redis: Redis = request.app.state.redis
        settings = request.app.state.settings
        times = getattr(settings, self.settings_attr)

        # 식별자: route key + IP. 운영은 JWT sub (인증된 사용자) + IP _이중_.
        client_ip = _client_ip(request)
        redis_key = f"{KEY_PREFIX}{self.key}:{client_ip}"

        async with redis.pipeline() as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, self.seconds, nx=True)
            results = await pipe.execute()
        count = int(results[0])

        if count > times:
            ttl = await redis.ttl(redis_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"rate limit exceeded — try again in {max(ttl, 1)}s",
                headers={"Retry-After": str(max(ttl, 1))},
            )


def _client_ip(request: Request) -> str:
    """프록시 뒤일 때 진짜 IP — `X-Forwarded-For` 첫 IP.

    경고: 프록시가 _신뢰_ 안 되면 클라이언트가 헤더 위조 가능. 운영은 _내부 프록시_ 가
    설정한 헤더만 신뢰 (Nginx/ALB 등이 자동 처리).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
