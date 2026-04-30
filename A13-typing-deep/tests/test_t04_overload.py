"""@overload / ParamSpec / TypeVarTuple 테스트."""

from __future__ import annotations

from typingdeep.t04_overload import first_and_rest, retried, split, timed


def test_overload_str() -> None:
    assert split("a,b,c") == ["a", "b", "c"]


def test_overload_bytes() -> None:
    assert split(b"a,b,c") == [b"a", b"b", b"c"]


def test_paramspec_preserves_signature() -> None:
    @timed
    def greet(name: str, *, loud: bool = False) -> str:
        return f"hi {name}!" if loud else f"hi {name}"

    assert greet("alice") == "hi alice"
    assert greet("alice", loud=True) == "hi alice!"


def test_paramspec_pep695() -> None:
    """PEP 695 의 `[**P, R]` 새 문법."""
    calls = 0

    @retried
    def flaky(x: int) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient")
        return x * 2

    # 첫 호출 실패 → 재시도 한 번 → 성공
    assert flaky(5) == 10
    assert calls == 2


def test_typevar_tuple_unpacking() -> None:
    head, rest = first_and_rest((1, "a", True, 3.14))
    assert head == 1
    assert rest == ("a", True, 3.14)
