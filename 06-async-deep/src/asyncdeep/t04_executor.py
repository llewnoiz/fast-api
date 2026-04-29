"""t04 — sync / CPU bound 작업을 async 에서 _안전하게_ 실행.

t03 에서 본 함정의 _해결책_. _꼭 sync 함수를 호출해야_ 한다면:
    - asyncio.to_thread(...)   ← 3.9+, 가장 권장
    - loop.run_in_executor(executor, fn, *args)
    - ThreadPoolExecutor 직접 사용

언제 어느 걸:
    sync I/O (예: requests, 표준 file I/O)  → ThreadPool (asyncio.to_thread)
    CPU bound (예: 큰 행렬 계산, 압축)        → ProcessPool (concurrent.futures)

비교:
    Kotlin:   withContext(Dispatchers.IO) { ... }
              withContext(Dispatchers.Default) { 무거운 계산 }
    Node:     worker_threads (CPU bound), libuv 가 알아서 (I/O)
    Java:     Executors.newFixedThreadPool + CompletableFuture.supplyAsync
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ProcessPoolExecutor

# ============================================================================
# 1) asyncio.to_thread — sync 함수를 _스레드 풀_ 에 보냄
# ============================================================================
#
# 이벤트 루프는 _자유로움_ → 그 사이 다른 코루틴 동작 가능.
# Kotlin 의 Dispatchers.IO 와 같은 자리.
# ============================================================================


def blocking_request(url: str) -> str:
    """sync 라이브러리 가정 (예: 표준 urllib, 옛날 requests). 학습용 fake."""
    time.sleep(0.2)
    return f"{url}:200"


async def fetch_via_thread(url: str) -> str:
    """sync 함수를 _스레드 풀_ 에서 실행 → 이벤트 루프 안 멈춤."""
    return await asyncio.to_thread(blocking_request, url)


# ============================================================================
# 2) CPU bound — ProcessPool (스레드 풀로는 GIL 때문에 진짜 병렬 X)
# ============================================================================
#
# Python 의 GIL: 한 프로세스 안에서 _Python 바이트코드_ 는 한 번에 한 스레드만 실행.
# 즉 CPU bound 는 스레드 풀로도 _진짜 병렬_ 안 됨 → 프로세스 풀 사용.
# 단, NumPy/orjson/ujson 같은 _C 확장_ 은 GIL 풀어서 진짜 병렬 가능.
# ============================================================================


def heavy_cpu(n: int) -> int:
    """CPU 점유 — 큰 합."""
    return sum(i * i for i in range(n))


async def crunch_with_processes(workloads: list[int]) -> list[int]:
    """ProcessPool 에 _무거운 계산_ 분산. 진짜 멀티코어 활용."""
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as pool:
        # run_in_executor: _현재_ 이벤트 루프에서 executor 에 실행 요청
        futures = [loop.run_in_executor(pool, heavy_cpu, n) for n in workloads]
        return await asyncio.gather(*futures)


# ============================================================================
# 3) 데모 — 둘 다 동시에 다른 async 와 함께
# ============================================================================


async def light_async_work(name: str) -> str:
    await asyncio.sleep(0.05)
    return name


async def main() -> None:
    print("=== 1) asyncio.to_thread — sync I/O 를 안전하게 ===")
    t0 = time.perf_counter()
    results = await asyncio.gather(
        fetch_via_thread("https://a"),
        fetch_via_thread("https://b"),
        fetch_via_thread("https://c"),
        light_async_work("L1"),         # 이벤트 루프 자유로워서 동시에 실행됨
    )
    print(f"  {(time.perf_counter() - t0) * 1000:.0f}ms  →  {results}")

    print("\n=== 2) ProcessPool — CPU bound 진짜 병렬 ===")
    t0 = time.perf_counter()
    sums = await crunch_with_processes([1_000_000, 1_000_000, 1_000_000, 1_000_000])
    print(f"  {(time.perf_counter() - t0) * 1000:.0f}ms  →  합 4개 끝 (첫 번째: {sums[0]})")


if __name__ == "__main__":
    asyncio.run(main())
