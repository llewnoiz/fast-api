"""Value Object 자가 검증 — 잘못된 값은 _존재 X_."""

from __future__ import annotations

import pytest
from tenderdomain.domain.exceptions import InvariantViolation
from tenderdomain.domain.value_objects import SKU, Money, OrderId, Quantity, UserId


def test_money_equality() -> None:
    assert Money(100, "KRW") == Money(100, "KRW")
    assert Money(100, "KRW") != Money(100, "USD")


def test_money_negative_rejected() -> None:
    with pytest.raises(InvariantViolation):
        Money(-1, "KRW")


def test_money_invalid_currency() -> None:
    with pytest.raises(InvariantViolation):
        Money(100, "krw")  # lowercase
    with pytest.raises(InvariantViolation):
        Money(100, "KOREA")  # too long


def test_money_add_same_currency() -> None:
    assert Money(100, "KRW").add(Money(50, "KRW")) == Money(150, "KRW")


def test_money_add_different_currency_rejected() -> None:
    with pytest.raises(InvariantViolation):
        Money(100, "KRW").add(Money(1, "USD"))


def test_money_multiply() -> None:
    assert Money(100, "KRW").multiply(3) == Money(300, "KRW")


def test_money_multiply_negative_rejected() -> None:
    with pytest.raises(InvariantViolation):
        Money(100, "KRW").multiply(-1)


def test_quantity_range() -> None:
    Quantity(1)
    Quantity(1000)
    with pytest.raises(InvariantViolation):
        Quantity(0)
    with pytest.raises(InvariantViolation):
        Quantity(1001)


def test_sku_format() -> None:
    SKU("ABC-1234")
    with pytest.raises(InvariantViolation):
        SKU("ABC-12345")  # 9 chars
    with pytest.raises(InvariantViolation):
        SKU("abc-1234")  # lowercase
    with pytest.raises(InvariantViolation):
        SKU("AB1-1234")  # digit in prefix


def test_id_value_objects() -> None:
    OrderId(1)
    UserId(1)
    with pytest.raises(InvariantViolation):
        OrderId(0)
    with pytest.raises(InvariantViolation):
        UserId(-1)
