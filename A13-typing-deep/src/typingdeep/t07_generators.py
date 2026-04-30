"""Generator — `yield` / `yield from` / `send` / `throw` / `close`.

Generator vs Iterator:
    Iterator: `__iter__` + `__next__` 가진 객체
    Generator: 함수가 `yield` 쓰면 _자동으로_ Iterator 반환

`yield` 의 깊이:
    1. _값 반환_ (단순)
    2. _값 받기_ (`x = yield value`) — 양방향
    3. _다른 generator 위임_ (`yield from`)
    4. async generator (`async def` + `yield`)

비교:
    JS: function* + yield — 거의 동일
    C#: yield return — IEnumerable 자동
    Kotlin: sequence { yield ... } — DSL 형태
"""

from __future__ import annotations

from collections.abc import Generator, Iterator


# ── 1. 단순 generator ──
def count_up_to(n: int) -> Generator[int, None, None]:
    """1..n yield. 무한 시퀀스도 가능 (메모리 절약)."""
    yield from range(1, n + 1)


# ── 2. 무한 generator + take 패턴 ──
def integers() -> Generator[int, None, None]:
    """1, 2, 3, ... 무한."""
    n = 1
    while True:
        yield n
        n += 1


def take[T](source: Iterator[T], n: int) -> list[T]:
    """무한 generator 에서 _N 개_ 만 추출."""
    result = []
    for _ in range(n):
        result.append(next(source))
    return result


# ── 3. yield from — 위임 ──
def flatten[T](nested: list[list[T]]) -> Generator[T, None, None]:
    """중첩 list → flat. `yield from inner` 가 inner generator 의 yield 를 _그대로_."""
    for inner in nested:
        yield from inner


# ── 4. 양방향: send() ──
def echo() -> Generator[str, str, None]:
    """`x = yield prompt` ── 외부에서 `gen.send(value)` 로 _값 전달_."""
    while True:
        received = yield "give me text"
        if received == "stop":
            return
        # received 가 send 로 들어온 값


# 사용:
#   gen = echo()
#   next(gen)              # priming — 'give me text' 받음
#   gen.send("hello")      # 다음 yield 까지 진행, "hello" 가 received 에 바인딩


# ── 5. close() / throw() ──
def cleanup_demo() -> Generator[int, None, None]:
    """`gen.close()` 시 GeneratorExit 예외 ── 자원 정리."""
    try:
        yield 1
        yield 2
        yield 3
    except GeneratorExit:
        # 자원 정리 — 파일 닫기 / DB 커넥션 반환
        pass


# ── 6. 변환 파이프라인 ──
def pipeline_demo(numbers: list[int]) -> list[int]:
    """generator 체인 — 메모리 효율 + 지연 평가."""

    def evens(src: Iterator[int]) -> Generator[int, None, None]:
        for n in src:
            if n % 2 == 0:
                yield n

    def squared(src: Iterator[int]) -> Generator[int, None, None]:
        for n in src:
            yield n * n

    return list(squared(evens(iter(numbers))))


# ── 7. async generator ──
async def async_count_up_to(n: int) -> AsyncGenerator[int, None]:  # noqa: F821
    """`async for x in gen:` 로 소비. WebSocket / SSE / DB 스트리밍 친화."""
    import asyncio  # noqa: PLC0415

    for i in range(1, n + 1):
        await asyncio.sleep(0)  # 진짜 I/O 대신 yield point
        yield i


from collections.abc import AsyncGenerator  # noqa: E402, I001 — 위 forward ref
