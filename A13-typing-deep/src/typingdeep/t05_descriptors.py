"""Descriptor — `__get__` / `__set__` / `__delete__` 로 _속성 접근 가로채기_.

Python 의 _숨은 마법_:
    - `@property` 가 _descriptor 의 한 형태_
    - 모든 _bound method_ 도 descriptor (`obj.method` 가 _자동_ 으로 self 바인딩)

언제 직접?
    - _재사용 가능한_ 검증 / 캐싱 / 변환 속성
    - SQLAlchemy `Column` 같은 ORM
    - Pydantic field 도 비슷한 역할

비교:
    Java: getter/setter 패턴 (boilerplate)
    Kotlin: `var` + custom get/set
    C#: property (`get`/`set`)
    JS: `Object.defineProperty` 또는 getter/setter
"""

from __future__ import annotations


# ── 검증 descriptor ────────────────────────────────────────────
class Positive:
    """양수만 허용. `Account.balance = -1` 시 `ValueError`."""

    def __set_name__(self, owner: type, name: str) -> None:
        """`Account.balance = Positive()` 시 `name="balance"` 자동 주입."""
        self._name = f"_{name}"

    def __get__(self, obj: object, objtype: type | None = None) -> int:
        if obj is None:
            return self  # type: ignore[return-value]
        return getattr(obj, self._name, 0)

    def __set__(self, obj: object, value: int) -> None:
        if value < 0:
            raise ValueError(f"must be positive: {value}")
        setattr(obj, self._name, value)


class Account:
    balance = Positive()  # 클래스 _속성_ 으로 — 모든 인스턴스 공유 descriptor

    def __init__(self, initial: int) -> None:
        self.balance = initial


# ── 지연 평가 descriptor (functools.cached_property 와 비슷) ──
class LazyProperty:
    """첫 접근 시 계산 + 캐시. 이후 접근은 즉시 반환."""

    def __init__(self, fn) -> None:  # noqa: ANN001
        self.fn = fn
        self._name = fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: object, objtype: type | None = None) -> object:
        if obj is None:
            return self
        # 첫 접근에만 fn() 실행 → 인스턴스 dict 에 저장 → 다음 접근부턴 _이쪽이 hit_
        value = self.fn(obj)
        obj.__dict__[self._name] = value
        return value


class Report:
    @LazyProperty
    def expensive_total(self) -> int:
        # 가짜 비싼 계산
        return sum(range(1000))
