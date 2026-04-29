"""분산 락 검증 — 두 코루틴 _동시에_ 같은 락 시도."""

from __future__ import annotations

import asyncio

import pytest
from cacheapp.lock import distributed_lock
from redis.asyncio import Redis

pytestmark = pytest.mark.integration


class TestDistributedLock:
    async def test_first_acquires_second_blocked(self, redis_client: Redis) -> None:
        """첫 번째가 락 잡으면 두 번째는 _획득 실패_ (blocking_timeout 짧게)."""
        # 첫 번째 — 잡고 _안 풀고_ 유지
        async with distributed_lock(redis_client, "demo", timeout=2.0, blocking_timeout=0.05) as got1:
            assert got1 is True

            # 두 번째 — 같은 키 시도, 못 잡음
            async with distributed_lock(
                redis_client, "demo", timeout=2.0, blocking_timeout=0.05
            ) as got2:
                assert got2 is False
        # 첫 번째 with 종료 = 락 해제

    async def test_serializes_concurrent_workers(self, redis_client: Redis) -> None:
        """두 워커가 _동시 시작_ 해도 critical section 은 _직렬_ 실행."""
        execution_order: list[str] = []

        async def worker(name: str, sleep_ms: int) -> None:
            async with distributed_lock(
                redis_client, "shared", timeout=2.0, blocking_timeout=2.0
            ) as got:
                if got:
                    execution_order.append(f"{name}-start")
                    await asyncio.sleep(sleep_ms / 1000)
                    execution_order.append(f"{name}-end")

        # 동시 시작
        await asyncio.gather(worker("A", 100), worker("B", 50))

        # 한 명이 시작하면 _그 명이 끝난 다음_ 다른 명이 시작 — 인터리빙 X
        assert execution_order in (
            ["A-start", "A-end", "B-start", "B-end"],
            ["B-start", "B-end", "A-start", "A-end"],
        )
