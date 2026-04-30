"""Saga orchestration 테스트 — 단위 테스트 (Redis 불필요)."""

from __future__ import annotations

from cachemqdeep.saga import Saga


async def test_saga_all_steps_succeed() -> None:
    async def step1(ctx: dict[str, object]) -> object:
        ctx["a"] = 1
        return "a-ok"

    async def step2(ctx: dict[str, object]) -> object:
        ctx["b"] = 2
        return "b-ok"

    saga = Saga().add_step("a", step1).add_step("b", step2)
    result = await saga.execute()
    assert result.succeeded
    assert result.completed_steps == ["a", "b"]
    assert result.compensated_steps == []
    assert result.context["a"] == 1


async def test_saga_compensates_in_reverse_on_failure() -> None:
    log: list[str] = []

    async def a_action(_: dict[str, object]) -> str:
        log.append("a-do")
        return "a"

    async def a_comp(_: dict[str, object]) -> None:
        log.append("a-undo")

    async def b_action(_: dict[str, object]) -> str:
        log.append("b-do")
        return "b"

    async def b_comp(_: dict[str, object]) -> None:
        log.append("b-undo")

    async def c_action(_: dict[str, object]) -> str:
        raise RuntimeError("c failed")

    saga = (
        Saga()
        .add_step("a", a_action, a_comp)
        .add_step("b", b_action, b_comp)
        .add_step("c", c_action)
    )
    result = await saga.execute()
    assert not result.succeeded
    assert result.completed_steps == ["a", "b"]
    # _역순_ 보상
    assert result.compensated_steps == ["b", "a"]
    assert log == ["a-do", "b-do", "b-undo", "a-undo"]


async def test_saga_skips_compensation_for_unstarted_step() -> None:
    async def a_action(_: dict[str, object]) -> str:
        return "a"

    async def a_comp(_: dict[str, object]) -> None:
        pass

    async def b_action(_: dict[str, object]) -> str:
        raise RuntimeError("b failed")

    async def b_comp(_: dict[str, object]) -> None:
        # b 가 _실패_ 했으니 보상 _안 함_ (정의에 따라). 본 구현은 completed_steps 에 안 들어가니 호출 안 됨.
        raise AssertionError("should not be called")

    saga = Saga().add_step("a", a_action, a_comp).add_step("b", b_action, b_comp)
    result = await saga.execute()
    assert not result.succeeded
    assert result.completed_steps == ["a"]
    assert result.compensated_steps == ["a"]
