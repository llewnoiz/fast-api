"""Generic 학습 모듈 테스트."""

from __future__ import annotations

import pytest
from typingdeep.t01_generics import (
    Box,
    OldBox,
    add_numeric,
    first,
    maximum,
    pair,
)


def test_old_box_inherits_list() -> None:
    box: OldBox[int] = OldBox([1, 2, 3])
    assert box.first() == 1
    assert OldBox[str]().first() is None


def test_pep695_box_value() -> None:
    box = Box(42)
    assert box.get() == 42


def test_pep695_box_map() -> None:
    box = Box("hello")
    new = box.map(len)
    assert new.get() == 5


def test_first_function() -> None:
    assert first([1, 2, 3]) == 1
    assert first([]) is None
    # 다른 타입도 OK — generic
    assert first(["a", "b"]) == "a"


def test_pair_preserves_types() -> None:
    p = pair(1, "two")
    assert p == (1, "two")


def test_constrained_typevar_int() -> None:
    assert add_numeric(1, 2) == 3


def test_constrained_typevar_float() -> None:
    assert add_numeric(1.5, 2.5) == 4.0


def test_maximum_picks_largest() -> None:
    assert maximum([3, 1, 4, 1, 5, 9, 2, 6]) == 9


def test_maximum_empty_raises() -> None:
    with pytest.raises(ValueError):
        maximum([])
