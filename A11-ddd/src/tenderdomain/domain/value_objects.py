"""Value Objects — _불변_ + _값으로_ 동일성 (id 없음).

핵심 규칙:
    1. **불변** — 생성 후 수정 X. 새 값이 필요하면 _새 인스턴스_ 만듦.
    2. **값으로 동일성** — `Money(100, "KRW") == Money(100, "KRW")`. id 비교 X.
    3. **자가 검증** — 생성자에서 _불변식_ 체크. 잘못된 VO 는 _존재 X_.
    4. **부수 효과 없음** — 메서드는 _순수_, 새 VO 반환.

VO vs Entity:
    Entity: id 가 _정체성_, 값 바뀌어도 같은 객체 (예: User, Order)
    VO:     값 자체가 _정체성_, 같은 값이면 같은 객체 (예: Money, Quantity, Email)

비교:
    Java records (16+) — `record Money(BigDecimal amount, String currency) {}`
    Kotlin data class
    C# struct + readonly
    TypeScript: 직접 `Object.freeze` 또는 라이브러리 (zod, io-ts)
"""

from __future__ import annotations

from dataclasses import dataclass

from tenderdomain.domain.exceptions import InvariantViolation


@dataclass(frozen=True)
class Money:
    """원화/달러 등 통화 + 금액. _정수 단위_ (KRW: 원, USD: 센트) — 부동소수점 _절대 X_.

    돈 계산은 부동소수점 → 절대 안 됨 (0.1 + 0.2 != 0.3). decimal 또는 정수.
    """

    amount: int  # 최소 단위 정수 (KRW=원, USD=cent)
    currency: str  # ISO 4217 (KRW / USD / EUR / JPY)

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise InvariantViolation(f"money amount must be >= 0: {self.amount}")
        if not self.currency or len(self.currency) != 3 or not self.currency.isupper():
            raise InvariantViolation(f"currency must be 3-letter uppercase: {self.currency!r}")

    def add(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise InvariantViolation(
                f"cannot add different currencies: {self.currency} vs {other.currency}"
            )
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, n: int) -> Money:
        if n < 0:
            raise InvariantViolation(f"multiplier must be >= 0: {n}")
        return Money(self.amount * n, self.currency)


@dataclass(frozen=True)
class Quantity:
    """주문 수량. 자가 검증."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise InvariantViolation(f"quantity must be >= 1: {self.value}")
        if self.value > 1000:
            raise InvariantViolation(f"quantity must be <= 1000: {self.value}")


@dataclass(frozen=True)
class SKU:
    """상품 식별자. 형식 강제 — `^[A-Z]{3}-[0-9]{4}$` (학습용)."""

    value: str

    def __post_init__(self) -> None:
        if len(self.value) != 8 or self.value[3] != "-":
            raise InvariantViolation(f"invalid SKU format: {self.value!r}")
        if not (self.value[:3].isupper() and self.value[:3].isalpha()):
            raise InvariantViolation(f"SKU prefix must be 3 uppercase letters: {self.value!r}")
        if not self.value[4:].isdigit():
            raise InvariantViolation(f"SKU suffix must be 4 digits: {self.value!r}")


@dataclass(frozen=True)
class OrderId:
    """주문 ID — 단순 int wrapper. _다른 ID 와 헷갈리지 않게_."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise InvariantViolation(f"order id must be >= 1: {self.value}")


@dataclass(frozen=True)
class UserId:
    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise InvariantViolation(f"user id must be >= 1: {self.value}")
