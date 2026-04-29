"""t01 — 이벤트 루프 기본.

Python 의 async I/O 모델 = **Node 와 _거의 같은_** 단일 스레드 이벤트 루프.
- 한 번에 _하나의 코루틴_ 만 실행
- I/O 대기(await) 시점에 _다른 코루틴_ 으로 전환
- CPU 작업은 _스레드 풀_ 로 보내야 함 (한 코루틴이 CPU 점유하면 _전체 멈춤_)

비교:
    Node:               같은 모델 (libuv 이벤트 루프)
    Kotlin coroutines:  같은 모델 + 구조적 동시성
    Java Project Loom:  Virtual Threads (다른 모델 — 가벼운 OS 스레드)
    Go:                 goroutine + 스케줄러 (또 다른 모델 — 다중 OS 스레드)

핵심 키워드:
    async def       — 코루틴 함수 정의
    await           — 다른 코루틴/awaitable 결과 기다림 (이때 이벤트 루프가 다른 일 함)
    asyncio.run()   — 이벤트 루프 시작 (앱 진입점에서 한 번)
    asyncio.sleep() — _이벤트 루프 친화_ 의 sleep (time.sleep ≠ )
"""

from __future__ import annotations

import asyncio
import time

# ============================================================================
# 1) 가장 단순한 코루틴 — 호출만 해도 _실행 안 됨_
# ============================================================================


async def hello() -> str:
    """async def 함수는 호출 시 _코루틴 객체_ 를 반환. 본체는 await 해야 실행."""
    return "안녕"


def demo_coroutine_object() -> None:
    coro = hello()                   # 본체 _아직 실행 안 됨_
    print("타입:", type(coro).__name__)
    print("객체:", coro)             # <coroutine object hello at ...>
    coro.close()                     # 안 쓸 거면 닫아주기 (warning 방지)


# ============================================================================
# 2) await — 코루틴 _안에서_ 다른 코루틴 결과 받기
# ============================================================================


async def greet(name: str) -> str:
    msg = await hello()              # await 가 _코루틴 본체를 실행_ 하고 결과 받음
    return f"{msg}, {name}"


# ============================================================================
# 3) asyncio.run — 이벤트 루프를 시작
# ============================================================================
#
# 비교:
#   Node:    실행 컨텍스트가 _이미_ 이벤트 루프 → 그냥 await 가능
#   Python:  CPython 은 sync 가 기본 → 진입점에서 asyncio.run() 으로 루프 시작
# ============================================================================


def demo_run() -> None:
    result = asyncio.run(greet("Alice"))   # 이벤트 루프 시작 → greet 실행 → 종료
    print("결과:", result)


# ============================================================================
# 4) asyncio.sleep vs time.sleep — async 의 핵심 함정 워밍업
# ============================================================================
#
# t03 에서 _깊이_ 다룸. 여기선 미리보기:
#   asyncio.sleep(1):  await 시점에 이벤트 루프가 _다른 일_ 함 (대기 1초)
#   time.sleep(1):     스레드 _전체_ 를 1초간 멈춤 → 이벤트 루프도 멈춤
# ============================================================================


async def task_async(name: str, sec: float) -> str:
    print(f"  [async] {name} 시작")
    await asyncio.sleep(sec)         # ← _양보_: 이벤트 루프가 다른 일 함
    print(f"  [async] {name} 끝")
    return name


def task_sync_blocking(name: str, sec: float) -> str:
    print(f"  [sync ] {name} 시작")
    time.sleep(sec)                  # ← _블로킹_: 이벤트 루프 멈춤
    print(f"  [sync ] {name} 끝")
    return name


def main() -> None:
    print("=== 1) 코루틴 객체 (실행 X) ===")
    demo_coroutine_object()

    print("\n=== 2) await — 다른 코루틴 결과 받기 ===")
    asyncio.run(greet("Alice"))      # 객체만 만들고 닫기

    print("\n=== 3) asyncio.run — 진입점 ===")
    demo_run()

    print("\n=== 4) asyncio.sleep 단독 실행 (1초) ===")
    asyncio.run(task_async("solo", 1.0))


if __name__ == "__main__":
    main()
