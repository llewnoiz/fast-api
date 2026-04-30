"""Generics — _타입 매개변수_ 로 재사용 가능한 컨테이너/함수.

Python 3.12+ 의 **PEP 695 새 문법** vs 옛 `TypeVar` 문법 _둘 다_ 보여줌.

비교:
    TypeScript: `class Box<T> {}` ── PEP 695 가 거의 동일
    Java:       `class Box<T> {}`
    Kotlin:     `class Box<T>`
    Go:         `type Box[T any] struct { v T }`
    C++:        `template<typename T> class Box {}`
"""

from __future__ import annotations

from typing import TypeVar

# ── 옛 문법 (Python 3.5+) ────────────────────────────────────────
T = TypeVar("T")  # 제약 없음 — 모든 타입
N = TypeVar("N", int, float)  # 제약: int 또는 float (Constrained)
B = TypeVar("B", bound="Comparable")  # bound: Comparable _및 그 자손_


class OldBox(list[T]):  # 옛 문법: list[T] 상속
    """`list[int]` 와 같은 시맨틱 + extra 메서드."""

    def first(self) -> T | None:
        return self[0] if self else None


# ── PEP 695 새 문법 (Python 3.12+) ─────────────────────────────
class Box[T]:
    """클래스 자체에 type parameter — 더 간결, 더 명확."""

    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value

    def map[U](self, fn: Callable[[T], U]) -> Box[U]:  # noqa: F821
        return Box(fn(self.value))


# 함수도 PEP 695 type parameter
def first[T](items: list[T]) -> T | None:
    return items[0] if items else None


def pair[A, B](a: A, b: B) -> tuple[A, B]:
    return (a, b)


# ── Constrained TypeVar ── (제약 가능한 타입만)
def add_numeric[N: (int, float)](a: N, b: N) -> N:
    """`int` 또는 `float` 만 ── `add_numeric("a", "b")` 는 type error."""
    return a + b


# ── Bounded TypeVar (PEP 695)
class Comparable:
    def __lt__(self, other: object) -> bool:
        return False  # 학습용 default — 실제 구현은 자식 클래스에서


def maximum[T: Comparable](items: list[T]) -> T:
    """`bound=Comparable` ── `<` 연산자 가진 타입만 허용.

    PEP 695 의 `[T: Comparable]` 이 _bound_ 표현.
    """
    if not items:
        raise ValueError("empty")
    best = items[0]
    for item in items[1:]:
        if best < item:
            best = item
    return best


# ── Variance: covariant / contravariant ──
# Python 의 _기본_ TypeVar 는 invariant (엄격).
# `T_co = TypeVar("T_co", covariant=True)` 로 공변 / `T_contra` contravariant.
# 보통 _읽기 전용_ 컨테이너 (Sequence) 가 covariant, _쓰기 전용_ (Sink) 가 contravariant.


# 학습용 import — 위에서 forward ref 로 썼던 것
from collections.abc import Callable  # noqa: E402, I001 — 데모 흐름 우선
