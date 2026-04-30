"""functools 심화 — `singledispatch` / `cache` / `partial` / `wraps` / `reduce`.

표준 라이브러리의 _고급 함수형 도구_. 알면 코드가 _짧아짐_.
"""

from __future__ import annotations

from functools import cache, lru_cache, partial, reduce, singledispatch, wraps
from typing import Any


# ── @singledispatch — 첫 인자 _타입 기반_ 분기 ──
# Java/Kotlin 의 메서드 오버로딩과 비슷한 효과.
@singledispatch
def render(value: object) -> str:
    """기본 분기 — 알 수 없는 타입."""
    return f"<unknown: {value!r}>"


@render.register
def _(value: int) -> str:
    return f"int={value}"


@render.register
def _(value: str) -> str:
    return f"str={value!r}"


@render.register(list)
def _(value: list[Any]) -> str:
    return f"list of {len(value)}"


# 사용:
#   render(42)         → "int=42"
#   render("hi")       → "str='hi'"
#   render([1, 2, 3])  → "list of 3"
#   render({"x": 1})   → "<unknown: ...>"


# ── @cache / @lru_cache — 메모이제이션 ──
@cache
def fib(n: int) -> int:
    """피보나치 — 캐시로 O(2^n) → O(n).

    `@cache` (3.9+) = `@lru_cache(maxsize=None)` 줄임.
    """
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


@lru_cache(maxsize=128)
def slow_lookup(key: str) -> int:
    """LRU 캐시 — 최대 128 개 보관, 가장 오래된 것부터 evict."""
    return hash(key)


# 주의: 캐시 키는 _해시 가능_ 해야 함. dict / list / 가변 객체는 X.
# 인스턴스 메서드에 `@cache` 쓰면 self 가 키에 포함 → 인스턴스 평생 살아있음.
# → `functools.cached_property` 가 _인스턴스 단위_ 캐시 (인스턴스 죽으면 같이 죽음).


# ── partial — 부분 적용 ──
def power(base: int, exp: int) -> int:
    return base**exp


square = partial(power, exp=2)
cube = partial(power, exp=3)
# square(5) = 25, cube(5) = 125

# 콜백 / 이벤트 핸들러에 _고정 인자_ 주입 (lambda 대안 — 더 빠름)


# ── @wraps — 데코레이터 메타데이터 보존 ──
def log_calls[**P, R](fn):  # noqa: ANN001, ANN201
    """데코레이터가 wraps 안 쓰면 `wrapper.__name__ == "wrapper"` 가 됨.

    @wraps 가 fn 의 `__name__` / `__doc__` / `__module__` 등을 wrapper 에 _복사_.
    """

    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        return fn(*args, **kwargs)

    return wrapper


@log_calls
def hello(name: str) -> str:
    """Greet someone."""
    return f"hi {name}"


# `hello.__name__` == "hello"  (wraps 없으면 "wrapper")
# `hello.__doc__` == "Greet someone."


# ── reduce — 누적 ──
def sum_squares(nums: list[int]) -> int:
    """`reduce(fn, iterable, init)` ── Java Stream `.reduce`."""
    return reduce(lambda acc, n: acc + n * n, nums, 0)


# 모던 Python 은 보통 `sum(n*n for n in nums)` _comprehension_ 이 더 가독성 좋음.
# reduce 는 _복잡한 누적_ (running max + count + ...) 에서 빛.
