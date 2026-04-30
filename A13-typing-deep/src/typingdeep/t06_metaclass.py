"""Metaclass — _클래스의 클래스_. 99% 의 코드는 _필요 없음_.

Python 클래스 생성 흐름:
    1. `class Foo: ...` ── 클래스 정의 _시점_ 에 metaclass 호출
    2. metaclass 가 _클래스 객체_ 만듦 (`type(name, bases, namespace)`)
    3. 인스턴스 생성은 `Foo()` ── `Foo.__call__` 호출

언제 _진짜로_ 필요?
    - 프레임워크 작성 (SQLAlchemy `DeclarativeBase`, Django Model)
    - DSL ── 클래스 정의 _자체_ 가 도메인 표현
    - **__init_subclass__ 가 거의 모든 경우 충분**

언제 _안_ 쓰는지 (권장):
    - 데코레이터로 충분하면 데코레이터
    - mixin / 상속으로 충분하면 그것
    - `__init_subclass__` 으로 충분하면 그것 (Python 3.6+)

비교:
    Java: annotation processor (컴파일 시점) ── metaclass 와 비슷한 _"클래스 가공"_
    Kotlin: KSP / 컴파일러 플러그인
    JS: 데코레이터 (TC39, 실험적)
"""

from __future__ import annotations

from typing import Any


# ── __init_subclass__ — 메타클래스의 _대안_ (90% 충분) ──
class Plugin:
    """모든 자식 클래스가 _자동 등록_ — 메타클래스 없이.

    Django / FastAPI 의 _라우터 자동 등록_ 같은 패턴.
    """

    registry: list[type[Plugin]] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        Plugin.registry.append(cls)


class HelloPlugin(Plugin):
    pass


class WorldPlugin(Plugin):
    pass


# `Plugin.registry` == `[HelloPlugin, WorldPlugin]` — 자동 누적


# ── 진짜 metaclass ── _진짜 필요할 때_
class Singleton(type):
    """singleton metaclass — 같은 클래스의 인스턴스를 _하나만_.

    경고: 단순 singleton 은 _module-level 변수_ 로 충분. 학습용 데모.
    """

    _instances: dict[type, object] = {}

    def __call__(cls, *args: object, **kwargs: object) -> object:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Config(metaclass=Singleton):
    def __init__(self, value: int = 42) -> None:
        self.value = value


# `Config(1) is Config(2)` ── True (둘 다 같은 인스턴스, 두 번째 호출은 init 안 됨)


# ── 실용 예: AutoRepr metaclass (학습용) ──
class AutoRepr(type):
    """모든 인스턴스에 `__repr__` 자동 — _필드 dump_."""

    def __new__(mcs, name: str, bases: tuple[type, ...], ns: dict[str, Any]) -> type:
        cls = super().__new__(mcs, name, bases, ns)
        if "__repr__" not in ns:

            def auto_repr(self: object) -> str:
                fields = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
                return f"{type(self).__name__}({fields})"

            cls.__repr__ = auto_repr  # type: ignore[assignment,method-assign]
        return cls


class User(metaclass=AutoRepr):
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age


# `repr(User("alice", 30))` == `"User(name='alice', age=30)"`
