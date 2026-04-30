"""Protocol — _구조적 타이핑_ (duck typing 의 타입 안전 버전).

Java/C# 의 _명시적_ interface 와 다름:
    - 클래스가 Protocol _상속 안 해도_ 구조 만족하면 OK
    - "이 메서드/속성 가진 모든 타입" 으로 추상화

비교:
    Go: interface — 구조적 typing 표준 (Protocol 의 영감)
    TypeScript: interface / type — 구조적 typing 기본
    Java: 명시적 implements — 거의 반대
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable


class Greeter(Protocol):
    """`greet()` 메서드 가진 모든 타입."""

    def greet(self) -> str: ...


def greet_all(greeters: Iterable[Greeter]) -> list[str]:
    return [g.greet() for g in greeters]


# 아래 두 클래스는 Protocol 을 _상속하지 않음_. 구조만 맞으면 사용 가능.
class English:
    def greet(self) -> str:
        return "Hello"


class Korean:
    def greet(self) -> str:
        return "안녕"


# `greet_all([English(), Korean()])` ── _둘 다 Greeter Protocol 만족_


# ── runtime_checkable ── isinstance() 가능
@runtime_checkable
class HasName(Protocol):
    name: str


def show_name(obj: object) -> str:
    """런타임에 _구조 검사_."""
    if isinstance(obj, HasName):
        return obj.name
    return "<unknown>"


# ── Callable Protocol — 시그니처가 정확한 함수만
class IntComparator(Protocol):
    def __call__(self, a: int, b: int) -> int: ...


def sort_with(items: list[int], cmp: IntComparator) -> list[int]:
    """파이썬 정렬은 key 기반이지만 _학습용_ 으로 cmp 패턴 시뮬레이션."""
    result = list(items)
    # 단순 버블 — 학습용
    n = len(result)
    for i in range(n):
        for j in range(0, n - i - 1):
            if cmp(result[j], result[j + 1]) > 0:
                result[j], result[j + 1] = result[j + 1], result[j]
    return result


# ── Generic Protocol ── (PEP 695)
class Repository[T](Protocol):
    """ID 로 T 조회."""

    def get(self, id: int) -> T | None: ...
    def add(self, item: T) -> None: ...
