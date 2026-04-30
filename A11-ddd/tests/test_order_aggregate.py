"""Order Aggregate 행동 — _순수 도메인_ 단위 테스트.

인프라 / FastAPI / DB 없이 _도메인 로직 자체_ 검증. DDD 의 _장점_.
"""

from __future__ import annotations

import pytest
from tenderdomain.domain.events import OrderCancelled, OrderPlaced
from tenderdomain.domain.exceptions import IllegalStateTransition, InvariantViolation
from tenderdomain.domain.order import Order, OrderLine, OrderStatus
from tenderdomain.domain.value_objects import SKU, Money, OrderId, Quantity, UserId


def _line(sku: str = "ABC-0001", qty: int = 1, price: int = 1000) -> OrderLine:
    return OrderLine(sku=SKU(sku), quantity=Quantity(qty), unit_price=Money(price, "KRW"))


def test_place_order_publishes_OrderPlaced_event() -> None:  # noqa: N802
    order = Order.place(
        order_id=OrderId(1),
        user_id=UserId(7),
        lines=[_line("ABC-0001", 2, 1000)],
    )
    assert order.status == OrderStatus.PLACED
    events = order.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], OrderPlaced)
    assert events[0].total == Money(2000, "KRW")


def test_place_empty_order_rejected() -> None:
    with pytest.raises(InvariantViolation):
        Order.place(order_id=OrderId(1), user_id=UserId(1), lines=[])


def test_same_sku_lines_merged() -> None:
    order = Order.place(
        order_id=OrderId(1),
        user_id=UserId(1),
        lines=[_line("ABC-0001", 2, 1000), _line("ABC-0001", 3, 1000)],
    )
    assert len(order.lines) == 1
    assert order.lines[0].quantity.value == 5


def test_total_sums_subtotals() -> None:
    order = Order.place(
        order_id=OrderId(1),
        user_id=UserId(1),
        lines=[
            _line("ABC-0001", 2, 1000),  # 2000
            _line("XYZ-9999", 3, 500),  # 1500
        ],
    )
    assert order.total() == Money(3500, "KRW")


def test_state_machine_valid_path() -> None:
    order = Order.place(order_id=OrderId(1), user_id=UserId(1), lines=[_line()])
    order.pay()
    assert order.status == OrderStatus.PAID
    order.ship()
    assert order.status == OrderStatus.SHIPPED
    order.complete()
    assert order.status == OrderStatus.COMPLETED


def test_pay_twice_rejected() -> None:
    order = Order.place(order_id=OrderId(1), user_id=UserId(1), lines=[_line()])
    order.pay()
    with pytest.raises(IllegalStateTransition):
        order.pay()


def test_ship_before_pay_rejected() -> None:
    order = Order.place(order_id=OrderId(1), user_id=UserId(1), lines=[_line()])
    with pytest.raises(IllegalStateTransition):
        order.ship()


def test_cancel_placed_order_emits_OrderCancelled() -> None:  # noqa: N802
    order = Order.place(order_id=OrderId(1), user_id=UserId(1), lines=[_line()])
    order.pull_events()  # OrderPlaced 비우기

    order.cancel("user requested")
    assert order.status == OrderStatus.CANCELLED
    events = order.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], OrderCancelled)
    assert events[0].reason == "user requested"


def test_cancel_shipped_order_rejected() -> None:
    order = Order.place(order_id=OrderId(1), user_id=UserId(1), lines=[_line()])
    order.pay()
    order.ship()
    with pytest.raises(IllegalStateTransition, match="must refund"):
        order.cancel("too late")


def test_cancel_already_cancelled_rejected() -> None:
    order = Order.place(order_id=OrderId(1), user_id=UserId(1), lines=[_line()])
    order.cancel("first time")
    with pytest.raises(IllegalStateTransition, match="already cancelled"):
        order.cancel("second")


def test_pull_events_clears_buffer() -> None:
    order = Order.place(order_id=OrderId(1), user_id=UserId(1), lines=[_line()])
    first = order.pull_events()
    second = order.pull_events()
    assert len(first) == 1
    assert second == []
