"""t02 — 동시 실행: gather / TaskGroup.

순차 await: 결과 _합산_ 시간만큼 걸림.
동시 실행:  _가장 오래 걸리는 하나_ 시간만 걸림 (병렬 X, 동시).

비교:
    Kotlin:  coroutineScope { listOf(async {...}, async {...}).awaitAll() }
    Node:    Promise.all([fetchA(), fetchB()])
    Java:    CompletableFuture.allOf(fa, fb).join()
    Go:      go fa(); go fb(); wg.Wait()  (다른 모델 — 다중 스레드)

이 모듈에서:
    1. 순차 await — 합산 시간
    2. asyncio.gather — 동시, 결과 _리스트_
    3. asyncio.gather(return_exceptions=True) — 일부 실패도 계속
    4. asyncio.TaskGroup (3.11+) — _구조적 동시성_, 더 안전
    5. asyncio.wait_for — 타임아웃
"""

from __future__ import annotations

import asyncio
import time


async def fetch(name: str, ms: int) -> str:
    """가짜 I/O — 진짜라면 httpx.get / db.fetch 자리."""
    await asyncio.sleep(ms / 1000)
    return f"{name}-result"


# ============================================================================
# 1) 순차 await — 합산 시간
# ============================================================================


async def sequential() -> tuple[float, list[str]]:
    t0 = time.perf_counter()
    a = await fetch("A", 200)
    b = await fetch("B", 300)
    c = await fetch("C", 100)
    return (time.perf_counter() - t0) * 1000, [a, b, c]


# ============================================================================
# 2) asyncio.gather — 동시 실행, 결과 _리스트_
# ============================================================================


async def with_gather() -> tuple[float, list[str]]:
    t0 = time.perf_counter()
    results = await asyncio.gather(
        fetch("A", 200),
        fetch("B", 300),
        fetch("C", 100),
    )
    # gather 는 사실 list 를 _런타임_ 에 반환하지만 mypy 가 가변 인자에선 tuple 로 추론.
    # list(...) 로 명시.
    return (time.perf_counter() - t0) * 1000, list(results)


# ============================================================================
# 3) gather + return_exceptions — 일부 실패해도 _전체_ 계속
# ============================================================================


async def fetch_or_fail(name: str, ms: int, fail: bool) -> str:
    await asyncio.sleep(ms / 1000)
    if fail:
        raise RuntimeError(f"{name} 실패")
    return f"{name}-ok"


async def with_gather_lenient() -> list[str | BaseException]:
    """`return_exceptions=True` — 예외도 _결과로_ 받음. 기본은 _첫 실패_ 시 전체 취소."""
    results = await asyncio.gather(
        fetch_or_fail("A", 100, fail=False),
        fetch_or_fail("B", 200, fail=True),
        fetch_or_fail("C", 100, fail=False),
        return_exceptions=True,
    )
    return list(results)


# ============================================================================
# 4) TaskGroup (3.11+) — 구조적 동시성, 더 안전
# ============================================================================
#
# Kotlin coroutineScope 와 _가장 비슷_:
#   - 블록을 벗어나기 전 _모든_ 자식 task 가 끝나길 기다림
#   - 하나가 실패하면 _다른 task 자동 취소_ (구조적)
#   - 예외가 ExceptionGroup 으로 모임
# ============================================================================


async def with_taskgroup() -> tuple[float, list[str]]:
    t0 = time.perf_counter()
    async with asyncio.TaskGroup() as tg:
        ta = tg.create_task(fetch("A", 200))
        tb = tg.create_task(fetch("B", 300))
        tc = tg.create_task(fetch("C", 100))
    # 블록 끝나면 _모든 task 완료 보장_
    return (time.perf_counter() - t0) * 1000, [ta.result(), tb.result(), tc.result()]


async def main() -> None:
    print("=== 1) 순차 await (합산 ≈ 600ms) ===")
    elapsed, results = await sequential()
    print(f"  {elapsed:.0f}ms  →  {results}")

    print("\n=== 2) asyncio.gather (가장 오래 걸린 것 ≈ 300ms) ===")
    elapsed, results = await with_gather()
    print(f"  {elapsed:.0f}ms  →  {results}")

    print("\n=== 3) gather(return_exceptions=True) ===")
    results_or_exc = await with_gather_lenient()
    for r in results_or_exc:
        print(f"  {type(r).__name__}: {r}")

    print("\n=== 4) TaskGroup (3.11+, 구조적 동시성) ===")
    elapsed, results = await with_taskgroup()
    print(f"  {elapsed:.0f}ms  →  {results}")


if __name__ == "__main__":
    asyncio.run(main())
