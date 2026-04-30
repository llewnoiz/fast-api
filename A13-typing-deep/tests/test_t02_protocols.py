"""Protocol — 구조적 typing 테스트."""

from __future__ import annotations

from typingdeep.t02_protocols import (
    English,
    HasName,
    Korean,
    greet_all,
    show_name,
    sort_with,
)


def test_protocol_satisfied_without_inheritance() -> None:
    """English / Korean 은 Protocol 상속 X — _구조만_ 맞으면 통과."""
    result = greet_all([English(), Korean()])
    assert result == ["Hello", "안녕"]


def test_runtime_checkable() -> None:
    class WithName:
        def __init__(self, name: str) -> None:
            self.name = name

    class NoName:
        pass

    assert isinstance(WithName("alice"), HasName) is True
    assert isinstance(NoName(), HasName) is False
    assert show_name(WithName("alice")) == "alice"
    assert show_name(NoName()) == "<unknown>"


def test_callable_protocol_signature() -> None:
    def less(a: int, b: int) -> int:
        return a - b

    sorted_asc = sort_with([3, 1, 2], less)
    assert sorted_asc == [1, 2, 3]
