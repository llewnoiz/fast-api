"""Context Manager 테스트."""

from __future__ import annotations

import pytest
from typingdeep.t08_context_managers import (
    AsyncTimer,
    SuppressErrors,
    Timer,
    timer,
)


def test_class_timer() -> None:
    with Timer() as t:
        pass
    assert t.elapsed >= 0


def test_decorator_timer() -> None:
    with timer() as state:
        pass
    assert state["elapsed"] >= 0


def test_suppress_errors_swallows_matching() -> None:
    with SuppressErrors(ValueError):
        raise ValueError("expected")
    # 여기 도달해야 — 예외 삼킴


def test_suppress_errors_propagates_other() -> None:
    with pytest.raises(KeyError), SuppressErrors(ValueError):
        raise KeyError("not value error")


def test_exit_called_even_on_exception() -> None:
    """`__exit__` 는 정상 / 예외 _둘 다_ 실행 — finally 효과."""
    t = Timer()
    with pytest.raises(RuntimeError), t:
        raise RuntimeError("boom")
    assert t.elapsed >= 0  # 측정 _완료_ — exit 호출됨


@pytest.mark.asyncio
async def test_async_context_manager() -> None:
    async with AsyncTimer() as t:
        pass
    assert t.elapsed >= 0
