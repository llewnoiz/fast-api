"""functools 심화 테스트."""

from __future__ import annotations

from typingdeep.t09_functools_advanced import (
    cube,
    fib,
    hello,
    render,
    square,
    sum_squares,
)


def test_singledispatch_int() -> None:
    assert render(42) == "int=42"


def test_singledispatch_str() -> None:
    assert render("hi") == "str='hi'"


def test_singledispatch_list() -> None:
    assert render([1, 2, 3]) == "list of 3"


def test_singledispatch_unknown() -> None:
    assert render({"k": 1}).startswith("<unknown:")


def test_cache_memoizes() -> None:
    """fib(30) 가 캐시 없으면 _수억 번_ 호출. 캐시면 즉시."""
    assert fib(30) == 832040
    # 캐시 hit 검증 — `fib.cache_info().hits > 0`
    info = fib.cache_info()
    assert info.hits > 0


def test_partial_squares_and_cubes() -> None:
    assert square(5) == 25
    assert cube(5) == 125


def test_wraps_preserves_metadata() -> None:
    assert hello.__name__ == "hello"
    assert hello.__doc__ == "Greet someone."


def test_reduce_sum_squares() -> None:
    assert sum_squares([1, 2, 3, 4]) == 1 + 4 + 9 + 16
    assert sum_squares([]) == 0
