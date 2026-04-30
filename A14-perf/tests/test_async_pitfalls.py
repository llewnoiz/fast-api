"""async 함정 패턴 검증."""

from __future__ import annotations

import asyncio

import pytest
from perfdeep.async_pitfalls import (
    blocking_good,
    cpu_bound,
    fetch_parallel,
    fetch_sequential,
    fire_and_track,
    run_cpu_in_thread,
)


@pytest.mark.asyncio
async def test_blocking_good_uses_async_sleep() -> None:
    result = await blocking_good(5)
    assert result == 5


@pytest.mark.asyncio
async def test_parallel_faster_than_sequential() -> None:
    """`gather` 가 _직렬_ 보다 빨라야 ── 같은 sleep 들이 병렬로."""
    items = [1, 2, 3, 4, 5]

    import time  # noqa: PLC0415

    t1 = time.monotonic()
    seq = await fetch_sequential(items)
    seq_time = time.monotonic() - t1

    t2 = time.monotonic()
    par = await fetch_parallel(items)
    par_time = time.monotonic() - t2

    assert seq == par == [2, 4, 6, 8, 10]
    # 병렬이 _명확히_ 빠름 (각 sleep 0.01s × 5 = 0.05s 직렬, 병렬은 ~0.01s)
    assert par_time < seq_time


@pytest.mark.asyncio
async def test_cpu_in_thread_returns_correct_result() -> None:
    """to_thread 로 CPU bound 함수 실행."""
    expected = cpu_bound(1000)
    result = await run_cpu_in_thread(1000)
    assert result == expected


@pytest.mark.asyncio
async def test_fire_and_track_collects_exceptions() -> None:
    """`gather(return_exceptions=True)` ── 실패도 _수집_."""

    async def ok() -> str:
        return "ok"

    async def fail() -> str:
        raise ValueError("boom")

    results = await fire_and_track([ok(), fail(), ok()])
    assert results[0] == "ok"
    assert isinstance(results[1], ValueError)
    assert results[2] == "ok"


@pytest.mark.asyncio
async def test_to_thread_does_not_block_loop() -> None:
    """to_thread 로 CPU bound 실행 _중에_ 다른 task 진행 가능."""

    progress: list[str] = []

    async def ticker() -> None:
        for _ in range(3):
            await asyncio.sleep(0.01)
            progress.append("tick")

    # CPU 작업과 ticker 동시
    await asyncio.gather(run_cpu_in_thread(100000), ticker())

    # ticker 가 _진행_ 됐어야 (CPU 작업이 루프 안 막음)
    assert len(progress) == 3
