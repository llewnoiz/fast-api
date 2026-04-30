"""TypeGuard 테스트."""

from __future__ import annotations

from typingdeep.t10_typeguard import is_int_list, sum_if_ints, sum_if_ints_naive


def test_is_int_list_true() -> None:
    assert is_int_list([1, 2, 3]) is True


def test_is_int_list_false_wrong_element() -> None:
    assert is_int_list([1, "two"]) is False


def test_is_int_list_false_not_list() -> None:
    assert is_int_list("hello") is False


def test_sum_if_ints_with_int_list() -> None:
    assert sum_if_ints([1, 2, 3]) == 6


def test_sum_if_ints_with_other() -> None:
    assert sum_if_ints("hi") == 0
    assert sum_if_ints([1, "two"]) == 0


def test_naive_version_also_works() -> None:
    """naive 버전도 _런타임_ 동작 동일 — 차이는 _mypy_ 만."""
    assert sum_if_ints_naive([1, 2, 3]) == 6
