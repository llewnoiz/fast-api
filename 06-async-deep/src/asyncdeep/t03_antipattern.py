"""t03 — async 의 _가장 큰 함정_: sync I/O 혼용.

이 모듈은 **왜 async 안에서 sync 함수를 부르면 안 되는지** 시각적으로 증명.

규칙:
    - async I/O 라이브러리 외부 → 무조건 _async 라이브러리_ 사용
    - 어쩔 수 없이 sync 만 있으면 → asyncio.to_thread / run_in_executor (t04)

실수 패턴:
    requests.get(...)        → httpx.AsyncClient
    time.sleep(...)          → asyncio.sleep
    open(...).read()         → aiofiles
    ssh subprocess           → asyncio.create_subprocess_exec
"""

from __future__ import annotations

import asyncio
import time


async def io_async(name: str, ms: int) -> str:
    """올바른 async I/O — await asyncio.sleep 으로 _이벤트 루프 양보_."""
    await asyncio.sleep(ms / 1000)
    return name


async def io_blocking(name: str, ms: int) -> str:
    """❌ async 안에서 sync 함수 호출 — 양보 _안 함_, 이벤트 루프 멈춤."""
    time.sleep(ms / 1000)             # ← async 함수 안의 _블로킹_ 호출
    return name


# ============================================================================
# 데모: 같은 3개 작업을 _3가지 방식_ 으로 → 시간 비교
# ============================================================================


async def all_async() -> float:
    """전부 async — gather 가 동시 실행 → 가장 오래 걸린 하나 시간."""
    t0 = time.perf_counter()
    await asyncio.gather(io_async("a", 200), io_async("b", 200), io_async("c", 200))
    return (time.perf_counter() - t0) * 1000


async def all_blocking() -> float:
    """❌ 전부 sync — gather 라도 _순차 실행_ 됨. 합산 시간."""
    t0 = time.perf_counter()
    await asyncio.gather(io_blocking("a", 200), io_blocking("b", 200), io_blocking("c", 200))
    return (time.perf_counter() - t0) * 1000


async def mixed() -> float:
    """❌ 일부만 sync — 그 한 코루틴이 이벤트 루프 점유 → 나머지도 멈춤."""
    t0 = time.perf_counter()
    await asyncio.gather(io_async("a", 200), io_blocking("b", 200), io_async("c", 200))
    return (time.perf_counter() - t0) * 1000


# ============================================================================
# 시각적 증명 — 누가 먼저 끝나는지
# ============================================================================


async def slow_sync(label: str) -> str:
    print(f"  [{label}] sync I/O 시작")
    time.sleep(0.5)                  # ❌ 이벤트 루프 0.5초간 _완전 멈춤_
    print(f"  [{label}] sync I/O 끝")
    return label


async def fast_async(label: str) -> str:
    print(f"  [{label}] async 시작")
    await asyncio.sleep(0.05)        # 짧은 비동기 대기
    print(f"  [{label}] async 끝")
    return label


async def proof_blocking_blocks_others() -> None:
    """slow_sync 가 이벤트 루프를 0.5초 막아서 fast_async 가 _그동안 못 돔_."""
    await asyncio.gather(
        slow_sync("BLOCK"),
        fast_async("FAST-1"),
        fast_async("FAST-2"),
    )


async def main() -> None:
    print("=== 1) 전부 async — gather 가 동시 (≈ 200ms 한 번) ===")
    elapsed = await all_async()
    print(f"  {elapsed:.0f}ms")

    print("\n=== 2) 전부 sync — gather 무력화, 순차 (≈ 600ms) ===")
    elapsed = await all_blocking()
    print(f"  {elapsed:.0f}ms")

    print("\n=== 3) 섞기 — 한 sync 가 다른 async 를 막음 ===")
    elapsed = await mixed()
    print(f"  {elapsed:.0f}ms  ← 동시여야 200ms 인데 더 걸림")

    print("\n=== 4) 시각적 증명 — sync 가 다른 task 를 멈춤 ===")
    print("    (FAST 들이 BLOCK 끝난 _다음에야_ 시작/끝나는지 보세요)")
    await proof_blocking_blocks_others()


if __name__ == "__main__":
    asyncio.run(main())
