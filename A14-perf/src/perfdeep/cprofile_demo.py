"""cProfile — 함수 단위 _누적 시간_ + 호출 수.

vs sampling profiler:
    cProfile (deterministic): _모든_ 함수 호출 기록. 정확. 오버헤드 ↑ (10~50x 느림).
    py-spy / pyinstrument (sampling): N ms 마다 stacktrace. 빠름. 짧은 함수 _누락_ 가능.

언제?
    - 함수 _많이_ 부르는데 _어떤 게 느린지_ 모를 때 → cProfile
    - 운영 _live_ 프로세스 보고 싶을 때 → py-spy (별도 프로세스)
"""

from __future__ import annotations

import cProfile
import io
import pstats
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def profile_call[T](fn: Callable[[], T]) -> tuple[T, str]:
    """`fn()` 호출 + cProfile 통계 텍스트 반환.

    반환:
        (result, stats_text) — `stats_text` 는 정렬된 함수별 시간 표.
    """
    profiler = cProfile.Profile()
    profiler.enable()
    result = fn()
    profiler.disable()

    buf = io.StringIO()
    stats = pstats.Stats(profiler, stream=buf).sort_stats(pstats.SortKey.CUMULATIVE)
    stats.print_stats(20)  # 상위 20 함수
    return result, buf.getvalue()


# ── 시연용 함수들 ──
def fib_naive(n: int) -> int:
    """O(2^n) 재귀 — cProfile 로 _재귀 호출 폭발_ 확인."""
    if n < 2:
        return n
    return fib_naive(n - 1) + fib_naive(n - 2)


def fib_iterative(n: int) -> int:
    """O(n) 반복 — 같은 결과, 훨씬 빠름."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def slow_string_concat(words: list[str]) -> str:
    """O(n²) 문자열 연결 — _모든 단계마다 새 문자열 생성_."""
    result = ""
    for w in words:
        result = result + w  # 매번 새 객체
    return result


def fast_string_concat(words: list[str]) -> str:
    """O(n) ── `"".join()` 가 _한 번에_ 알고리즘 인지하고 buffer 할당."""
    return "".join(words)
