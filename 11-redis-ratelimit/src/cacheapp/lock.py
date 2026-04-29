"""분산 락 — `SET NX EX` 기반.

비교:
    Spring:    Spring Integration `RedisLockRegistry`, Redisson (가장 풍부)
    NestJS:    redlock 라이브러리
    Java:      Redisson `RLock` (multi-node Redlock 알고리즘)

언제 쓰나:
    - 같은 사용자의 _동시 요청_ 직렬화 (예: 결제 중복 방지)
    - 분산 환경에서 _주기적 작업_ 한 인스턴스만 실행 (cron leader election)
    - 캐시 stampede 방지 (rebuild 시 락)

주의:
    - 락 timeout 은 _작업 최대 시간_ 보다 길게 — 너무 짧으면 다른 워커가 동시 진입
    - 너무 길면 워커 죽었을 때 _복구 지연_
    - 본격적인 분산 환경엔 _Redlock 알고리즘_ 권장 (단일 Redis 는 SPOF)
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from redis.asyncio import Redis


@contextlib.asynccontextmanager
async def distributed_lock(
    redis: Redis,
    key: str,
    *,
    timeout: float = 10.0,        # 락 자동 해제 시간 (deadlock 방지)
    blocking_timeout: float = 5.0,  # 락 획득 _대기_ 최대 시간
) -> AsyncIterator[bool]:
    """분산 락 컨텍스트 매니저.

    blocking_timeout 안에 못 잡으면 `False` yield — 호출자가 _획득 실패_ 처리.

    사용:
        async with distributed_lock(redis, "order:42") as got:
            if not got:
                raise HTTPException(429, "다른 요청 처리 중")
            # critical section
    """
    lock = redis.lock(key, timeout=timeout, blocking_timeout=blocking_timeout)
    acquired = await lock.acquire()
    try:
        yield bool(acquired)
    finally:
        if acquired:
            # 이미 만료/다른 owner 가 점유 — 조용히 무시
            with contextlib.suppress(Exception):
                await lock.release()
