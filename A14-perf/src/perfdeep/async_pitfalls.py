"""async 성능 함정 — _자주 마주치는_ 5가지.

함정 1. **async 안에서 blocking 호출** — 이벤트 루프 _전체_ 멈춤.
함정 2. **순차 await** — `await a; await b;` 가 _직렬_ 실행. 병렬은 `gather`.
함정 3. **잘못된 sleep** — `time.sleep()` (X) vs `asyncio.sleep()` (O).
함정 4. **CPU bound 을 async 로** — async 의 _이점 X_, executor 가 정답.
함정 5. **닫지 않은 task** — `create_task` 후 await 안 함 → silent 실패.

탐지 도구:
    - `asyncio.get_event_loop().slow_callback_duration = 0.1` → 100ms 이상 동기 callback 경고
    - `aiomonitor` ── 운영 monitor
    - `pyinstrument` ── async 친화 sampling profiler
"""

from __future__ import annotations

import asyncio
import time


# ── 함정 1: blocking 호출 ──
async def blocking_bad(n: int) -> int:
    """`time.sleep` 은 _이벤트 루프 전체_ 멈춤. 동시 요청 _다_ 멈춤."""
    time.sleep(n / 1000)  # 잘못!
    return n


async def blocking_good(n: int) -> int:
    """`asyncio.sleep` ── 이벤트 루프 _yield_, 다른 태스크 진행."""
    await asyncio.sleep(n / 1000)
    return n


# ── 함정 2: 순차 vs 병렬 ──
async def fetch_sequential(items: list[int]) -> list[int]:
    """N 개 _직렬_ ── 총 시간 = sum(각 시간)."""
    results = []
    for n in items:
        await asyncio.sleep(0.01)
        results.append(n * 2)
    return results


async def fetch_parallel(items: list[int]) -> list[int]:
    """`gather` ── 총 시간 = max(각 시간)."""

    async def one(n: int) -> int:
        await asyncio.sleep(0.01)
        return n * 2

    return list(await asyncio.gather(*[one(n) for n in items]))


# ── 함정 3: blocking sync 함수를 executor 로 ──
def cpu_bound(n: int) -> int:
    """순수 CPU — async 로는 _이득 없음_."""
    total = 0
    for i in range(n):
        total += i * i
    return total


async def run_cpu_in_thread(n: int) -> int:
    """`asyncio.to_thread` ── _스레드 풀_ 에 위임 + await.

    GIL 때문에 _CPU bound_ 는 진짜 병렬 X. 그래도 _이벤트 루프 막지 않음_.
    완전 병렬은 `ProcessPoolExecutor`.
    """
    return await asyncio.to_thread(cpu_bound, n)


async def run_cpu_in_process(n: int) -> int:
    """진짜 병렬 — 별도 프로세스 (GIL 우회). 비용: _IPC + 직렬화_."""
    loop = asyncio.get_running_loop()
    from concurrent.futures import ProcessPoolExecutor  # noqa: PLC0415

    with ProcessPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, cpu_bound, n)


# ── 함정 5: 누락된 await ──
async def fire_and_forget_bad() -> None:
    """`create_task` 후 await 안 함 → 예외 발생해도 _조용히_."""

    async def fail() -> None:
        raise RuntimeError("silent failure")

    _ = asyncio.create_task(fail())  # noqa: RUF006 — 의도적 (잘못된 패턴 데모)
    # 함수 종료 → task 가 _gc 될 때_ 경고만


async def fire_and_track(coros: list) -> list[BaseException | object]:  # noqa: ANN001
    """`gather(..., return_exceptions=True)` ── 모든 실패 _수집_."""
    return list(await asyncio.gather(*coros, return_exceptions=True))


# ── 탐지: slow_callback_duration ──
def enable_slow_callback_warning(threshold_seconds: float = 0.1) -> None:
    """100ms 이상 동기 콜백 → 로그 경고. 개발 / 스테이징에서 _의심_ 발견용.

    운영 enable 시 _노이즈_ 가능 — 조절.
    """
    loop = asyncio.get_event_loop()
    loop.slow_callback_duration = threshold_seconds
