"""t06 — async generator + async for.

비교:
    Kotlin:   Flow { emit(x) } / suspend 함수 안에서
    Node/JS:  async function* () { yield x } / for await (...)
    Java:     Flow API (Reactive Streams)
    Go:       채널 + range

언제 쓰나:
    - **스트리밍 응답** (Server-Sent Events, NDJSON, 큰 파일 다운로드)
    - **점진적 처리** (한 번에 다 메모리에 안 올림)
    - DB 결과 페이지네이션
    - 메시지 큐 컨슈머 (13 단계)

FastAPI 의 `StreamingResponse` 가 내부적으로 async iterator 를 사용.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

# ============================================================================
# 1) async generator — yield 가 _코루틴 안에서_
# ============================================================================


async def stream_numbers(n: int) -> AsyncIterator[int]:
    """0..n-1 을 _점진적_ 으로 산출. await 가능."""
    for i in range(n):
        await asyncio.sleep(0.05)        # 가짜 I/O — DB cursor / Kafka poll 자리
        yield i


# ============================================================================
# 2) async for — 소비
# ============================================================================


async def consume() -> list[int]:
    """async for 로 _하나씩_ 받기."""
    out: list[int] = []
    async for value in stream_numbers(5):
        print(f"  받음: {value}")
        out.append(value)
    return out


# ============================================================================
# 3) async generator + 변환 (filter / map)
# ============================================================================


async def even_squares(source: AsyncIterator[int]) -> AsyncIterator[int]:
    """다른 async iterator 를 입력받아 _변환_ 해서 산출 — 파이프라인 패턴."""
    async for x in source:
        if x % 2 == 0:
            yield x * x


# ============================================================================
# 4) FastAPI StreamingResponse 패턴 (가짜)
# ============================================================================


async def event_stream() -> AsyncIterator[bytes]:
    """SSE 스타일 이벤트 스트림 — FastAPI 라우트가 이걸 그대로 yield 하면 _점진_ 응답."""
    for i in range(3):
        await asyncio.sleep(0.1)
        yield f"event: tick\ndata: {i}\n\n".encode()


async def main() -> None:
    print("=== 1) async generator + async for ===")
    out = await consume()
    print(f"  결과: {out}")

    print("\n=== 2) 변환 파이프라인 (even_squares) ===")
    async for v in even_squares(stream_numbers(8)):
        print(f"  변환 결과: {v}")

    print("\n=== 3) SSE 스타일 스트림 (raw bytes) ===")
    async for chunk in event_stream():
        print(f"  chunk: {chunk!r}")


if __name__ == "__main__":
    asyncio.run(main())
