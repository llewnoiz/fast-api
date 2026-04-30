"""cProfile 사용 패턴 검증."""

from __future__ import annotations

from perfdeep.cprofile_demo import (
    fast_string_concat,
    fib_iterative,
    fib_naive,
    profile_call,
    slow_string_concat,
)


def test_profile_call_returns_stats() -> None:
    """결과 + 통계 텍스트 둘 다 반환."""
    words = ["hello"] * 100
    result, stats = profile_call(lambda: fast_string_concat(words))
    assert result == "hello" * 100
    # 통계에 함수명 등장
    assert "fast_string_concat" in stats or "<lambda>" in stats


def test_fib_iterative_matches_naive_for_small_n() -> None:
    """검증 — 빠른 버전이 _같은 결과_."""
    for n in range(15):
        assert fib_iterative(n) == fib_naive(n)


def test_string_concat_methods_same_result() -> None:
    words = ["a", "b", "c", "d"]
    assert slow_string_concat(words) == fast_string_concat(words) == "abcd"
