"""Context Manager — `with` 문 + `__enter__/__exit__` (또는 `@contextmanager`).

용도:
    - 자원 _획득 / 해제_ 보장 (파일, 락, DB 트랜잭션, 임시 디렉토리)
    - 상태 _임시 변경_ (timezone, log level, mock)
    - 측정 / 로깅 / 트레이싱 boundary

비교:
    Java: try-with-resources (`AutoCloseable`)
    C#: `using` (IDisposable)
    Go: `defer`
    Rust: RAII (Drop trait)
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from types import TracebackType


# ── 클래스 기반 ── 가장 명시적
class Timer:
    """`with Timer() as t: ...; print(t.elapsed)`."""

    def __init__(self) -> None:
        self.start: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self.start = time.monotonic()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.elapsed = time.monotonic() - self.start
        # `return False` (또는 None) → 예외 _재전파_. `return True` → _삼킴_.


# ── @contextmanager 데코레이터 ── 더 짧은 코드
@contextmanager
def timer() -> Generator[dict[str, float], None, None]:
    """generator 한 줄 패턴: yield 위가 enter, 아래가 exit."""
    state = {"start": time.monotonic(), "elapsed": 0.0}
    try:
        yield state
    finally:
        # 예외 / 정상 _둘 다_ finally 가 잡음
        state["elapsed"] = time.monotonic() - state["start"]


# ── 예외 _삼키기_ ──
class SuppressErrors:
    """특정 예외만 _조용히_ 무시. 운영용은 `contextlib.suppress` 사용."""

    def __init__(self, *exc_types: type[BaseException]) -> None:
        self.exc_types = exc_types

    def __enter__(self) -> SuppressErrors:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        # True 반환 → 예외 삼킴. _isinstance 검사_ 로 종류 좁힘.
        return exc is not None and isinstance(exc, self.exc_types)


# ── async context manager ──
class AsyncTimer:
    """`async with AsyncTimer() as t: ...`."""

    def __init__(self) -> None:
        self.elapsed: float = 0.0
        self._start: float = 0.0

    async def __aenter__(self) -> AsyncTimer:
        self._start = time.monotonic()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.elapsed = time.monotonic() - self._start


# ── 중첩 / 다중 ── (Python 3.10+)
# `with timer() as t1, open(...) as f, lock:` 가 _하나의 with_ 로 묶임 (PEP 617).
