"""t05 — 타임아웃과 취소.

비교:
    Kotlin:   withTimeout(500) { ... } / withTimeoutOrNull
    Node:     AbortController + AbortSignal.timeout(500)
    Java:     CompletableFuture.orTimeout(500, MS)
    Go:       context.WithTimeout(ctx, 500*time.Millisecond)

Python:
    asyncio.timeout(0.5) 컨텍스트 매니저  (3.11+, 가장 권장)
    asyncio.wait_for(coro, 0.5)            (옛날 방식, 단일 코루틴)
    Task.cancel()                          (수동 취소)

핵심:
    - 취소는 _CancelledError 예외_ 로 코루틴에 도착
    - cleanup 은 try/finally 또는 async with 로
    - cancel 후엔 _꼭 await_ 해서 정리 마치게 (안 그러면 RuntimeWarning)
"""

from __future__ import annotations

import asyncio
import time


async def slow_task(name: str, sec: float) -> str:
    try:
        print(f"  [{name}] 시작")
        await asyncio.sleep(sec)
        print(f"  [{name}] 정상 완료")
        return name
    except asyncio.CancelledError:
        # 취소 시 _감지_ 해서 정리 가능. 다시 raise 해야 _진짜 취소됨_.
        print(f"  [{name}] 취소됨 (정리 중)")
        raise


# ============================================================================
# 1) asyncio.timeout — 컨텍스트 매니저 (3.11+)
# ============================================================================


async def with_timeout_ok() -> None:
    async with asyncio.timeout(0.5):
        result = await slow_task("FAST", 0.1)
        print(f"  결과: {result}")


async def with_timeout_exceeded() -> None:
    try:
        async with asyncio.timeout(0.2):     # 0.2초만 허용
            await slow_task("SLOW", 1.0)     # 1초 걸리는 작업
    except TimeoutError:
        print("  ⏱  타임아웃 — TimeoutError 잡음")


# ============================================================================
# 2) asyncio.wait_for — 옛날 방식 (여전히 유효)
# ============================================================================


async def with_wait_for() -> None:
    try:
        result = await asyncio.wait_for(slow_task("WAIT", 1.0), timeout=0.2)
        print(f"  결과: {result}")
    except TimeoutError:
        print("  ⏱  asyncio.wait_for 타임아웃")


# ============================================================================
# 3) 수동 취소 — Task.cancel()
# ============================================================================


async def manual_cancel() -> None:
    task = asyncio.create_task(slow_task("CANCELME", 5.0))
    await asyncio.sleep(0.2)         # 0.2초 후 취소 결정
    task.cancel()
    try:
        await task                   # 정리 _기다리기_ 필수
    except asyncio.CancelledError:
        print("  취소 완료")


# ============================================================================
# 4) TaskGroup 의 _자동 취소_ — 한 task 실패 → 형제들 취소
# ============================================================================


async def auto_cancel_in_taskgroup() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(slow_task("SIBLING-1", 2.0))
            tg.create_task(slow_task("SIBLING-2", 2.0))
            tg.create_task(slow_task("FAIL-FAST", 0.1))
            await asyncio.sleep(0.15)
            raise ValueError("의도적 실패")  # ← 형제들 자동 취소됨
    except* ValueError as eg:           # ExceptionGroup (3.11+) 잡기
        print(f"  TaskGroup 예외 그룹: {[str(e) for e in eg.exceptions]}")


async def main() -> None:
    print("=== 1) asyncio.timeout — 정상 ===")
    await with_timeout_ok()

    print("\n=== 2) asyncio.timeout — 초과 ===")
    await with_timeout_exceeded()

    print("\n=== 3) asyncio.wait_for ===")
    await with_wait_for()

    print("\n=== 4) 수동 Task.cancel() ===")
    await manual_cancel()

    print("\n=== 5) TaskGroup 자동 취소 (3.11+) ===")
    t0 = time.perf_counter()
    await auto_cancel_in_taskgroup()
    print(f"  걸린 시간: {(time.perf_counter() - t0) * 1000:.0f}ms (5초 안 기다리고 빨리 끝남)")


if __name__ == "__main__":
    asyncio.run(main())
