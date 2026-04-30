"""Generator 테스트."""

from __future__ import annotations

import pytest
from typingdeep.t07_generators import (
    async_count_up_to,
    count_up_to,
    echo,
    flatten,
    integers,
    pipeline_demo,
    take,
)


def test_count_up_to() -> None:
    assert list(count_up_to(5)) == [1, 2, 3, 4, 5]


def test_take_from_infinite() -> None:
    assert take(integers(), 5) == [1, 2, 3, 4, 5]


def test_yield_from_flatten() -> None:
    assert list(flatten([[1, 2], [3], [4, 5, 6]])) == [1, 2, 3, 4, 5, 6]


def test_send_to_generator() -> None:
    """`gen.send(value)` 가 `x = yield prompt` 의 _x_ 가 됨."""
    gen = echo()
    prompt = next(gen)  # priming
    assert prompt == "give me text"

    next_prompt = gen.send("hello")
    assert next_prompt == "give me text"

    # "stop" 보내면 generator 종료 → StopIteration
    with pytest.raises(StopIteration):
        gen.send("stop")


def test_pipeline_evens_squared() -> None:
    """1,2,3,4,5 → 짝수 (2,4) → 제곱 (4, 16)."""
    assert pipeline_demo([1, 2, 3, 4, 5]) == [4, 16]


@pytest.mark.asyncio
async def test_async_generator() -> None:
    result = []
    async for v in async_count_up_to(3):
        result.append(v)
    assert result == [1, 2, 3]
