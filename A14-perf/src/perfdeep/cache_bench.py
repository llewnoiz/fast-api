"""캐시 효과 측정 — `@cache` / `@lru_cache` / `cached_property`.

배경 (A13 t09 의 확장):
    - 메모이제이션은 _연산 비용_ ≫ _캐시 lookup 비용_ 일 때만 이득
    - 짧은 함수 (산술 한 줄) 에 캐시 = _오히려 느려짐_

원칙:
    "**measure**, don't assume."
"""

from __future__ import annotations

from functools import cache, cached_property


# ── _재귀_ ── 캐시가 _O(2^n) → O(n)_ 으로 감소
def fib_no_cache(n: int) -> int:
    if n < 2:
        return n
    return fib_no_cache(n - 1) + fib_no_cache(n - 2)


@cache
def fib_with_cache(n: int) -> int:
    if n < 2:
        return n
    return fib_with_cache(n - 1) + fib_with_cache(n - 2)


# ── _짧은_ 함수 ── 캐시 _오버헤드_ 가 더 클 수 있음
@cache
def add_with_cache(a: int, b: int) -> int:
    return a + b


def add_no_cache(a: int, b: int) -> int:
    return a + b


# ── cached_property — 인스턴스 단위 ──
class ExpensiveReport:
    """`expensive_total` 첫 접근 = 계산. 두 번째부턴 _instance dict_ hit."""

    def __init__(self, data: list[int]) -> None:
        self.data = data

    @cached_property
    def expensive_total(self) -> int:
        return sum(x * x for x in self.data)
