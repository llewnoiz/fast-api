"""Metaclass / __init_subclass__ 테스트."""

from __future__ import annotations

from typingdeep.t06_metaclass import (
    Config,
    HelloPlugin,
    Plugin,
    User,
    WorldPlugin,
)


def test_init_subclass_auto_registers() -> None:
    """`__init_subclass__` ── 자식 정의되면 _자동_ registry 추가."""
    assert HelloPlugin in Plugin.registry
    assert WorldPlugin in Plugin.registry


def test_singleton_metaclass() -> None:
    a = Config(value=1)
    b = Config(value=2)
    assert a is b
    # _첫 호출_ 의 init 만 실행 — value 는 1 그대로
    assert a.value == 1


def test_auto_repr_metaclass() -> None:
    u = User(name="alice", age=30)
    assert repr(u) == "User(name='alice', age=30)"
