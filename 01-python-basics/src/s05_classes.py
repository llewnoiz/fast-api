"""05 — 클래스 / dataclass / enum / Protocol.

Python 의 OOP 는 자유롭다 (모든 멤버 public, ABC 가 인터페이스 역할).
데이터 객체는 `@dataclass`, 열거형은 `Enum`, 구조적 타입은 `Protocol`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol


# ---------- 기본 클래스 ----------
class Account:
    """은행 계좌. self 는 _명시적_ 으로 매개변수에 작성."""

    # 클래스 변수 (Java static 필드)
    interest_rate: float = 0.02

    def __init__(self, owner: str, balance: float = 0.0) -> None:
        self.owner = owner            # 인스턴스 변수
        self._balance = balance       # `_` 접두사: 관용적으로 protected (강제 X)

    # ---------- 매직 메서드 ----------
    def __repr__(self) -> str:
        # 디버깅용 표현 — 보통 `__class__(...)` 형태로
        return f"Account(owner={self.owner!r}, balance={self._balance})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Account) and self.owner == other.owner

    def __hash__(self) -> int:
        return hash(self.owner)

    # ---------- property: getter/setter ----------
    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if value < 0:
            raise ValueError("음수 잔고 불가")
        self._balance = value

    # ---------- 인스턴스 / 클래스 / 정적 메서드 ----------
    def deposit(self, amount: float) -> None:
        self.balance += amount  # property setter 호출됨

    @classmethod
    def from_str(cls, s: str) -> Account:
        """팩토리 — Java 의 static factory method."""
        owner, balance = s.split(":")
        return cls(owner, float(balance))

    @staticmethod
    def is_valid_owner(name: str) -> bool:
        return len(name) >= 2


# ---------- 상속 ----------
class SavingsAccount(Account):
    def __init__(self, owner: str, balance: float = 0.0, rate: float = 0.05) -> None:
        super().__init__(owner, balance)
        self.rate = rate

    def accrue(self) -> None:
        self._balance *= 1 + self.rate


# ---------- @dataclass — boilerplate 자동 생성 (Java record / Lombok) ----------
@dataclass
class Point:
    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass(frozen=True, slots=True)
class User:
    """frozen=True: 불변 (Java record 동등). slots=True: 메모리 절약."""
    id: int
    name: str
    tags: list[str] = field(default_factory=list)  # mutable default 함정 회피

    def __post_init__(self) -> None:
        # 검증 — Pydantic 등장 전까지 흔한 패턴
        if self.id < 0:
            raise ValueError("id 는 음수 불가")


# ---------- Enum ----------
class OrderStatus(Enum):
    PENDING = auto()
    PAID = auto()
    SHIPPED = auto()
    DELIVERED = auto()
    CANCELED = auto()

    def is_terminal(self) -> bool:
        return self in {OrderStatus.DELIVERED, OrderStatus.CANCELED}


# ---------- Protocol — 구조적 타이핑 (Go 인터페이스와 비슷) ----------
class HasLength(Protocol):
    def __len__(self) -> int: ...


def total_length(items: list[HasLength]) -> int:
    """선언적으로 'HasLength 인터페이스를 따르는 모든 것' 을 받음.
    실제 클래스가 HasLength 를 명시적으로 implements 안 해도 됨 (duck typing).
    """
    return sum(len(it) for it in items)


def main() -> None:
    print("=== 클래스 ===")
    a = Account("Alice", 1000)
    a.deposit(500)
    print(a)
    print("balance:", a.balance)
    try:
        a.balance = -10  # property setter 가 막음
    except ValueError as e:
        print("setter 검증:", e)

    print("\n=== 상속 ===")
    s = SavingsAccount("Bob", 1000, rate=0.1)
    s.accrue()
    print(s, "→ balance:", s.balance)

    print("\n=== dataclass ===")
    p1 = Point(0, 0)
    p2 = Point(3, 4)
    print("거리:", p1.distance_to(p2))

    u = User(1, "Alice", ["admin"])
    print(u)
    # u.name = "X"  # frozen → FrozenInstanceError

    print("\n=== Enum ===")
    s_ = OrderStatus.PAID
    print(s_, s_.is_terminal())
    print(OrderStatus.DELIVERED, OrderStatus.DELIVERED.is_terminal())

    print("\n=== Protocol ===")
    items: list[HasLength] = ["abc", [1, 2, 3, 4], {"a": 1, "b": 2}]
    print("total length:", total_length(items))


if __name__ == "__main__":
    main()
