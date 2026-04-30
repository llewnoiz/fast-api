"""GetOrder Query — _읽기_ use case.

CQRS 가벼운 적용: Command (PlaceOrder/CancelOrder) 는 Aggregate 변경 + 이벤트, Query 는 _read DTO_ 반환만.

A7 의 CQRS 와 비교: 본 모듈은 _Aggregate 도메인 모델 그대로 읽기_ (간단). A7 는 별도 read model.
"""

from __future__ import annotations

from dataclasses import dataclass

from tenderdomain.domain.exceptions import OrderNotFound
from tenderdomain.domain.order import OrderStatus
from tenderdomain.domain.value_objects import OrderId
from tenderdomain.ports.uow import UnitOfWork


@dataclass(frozen=True)
class OrderLineDTO:
    sku: str
    quantity: int
    unit_amount: int


@dataclass(frozen=True)
class GetOrderOutput:
    order_id: int
    user_id: int
    status: OrderStatus
    lines: list[OrderLineDTO]
    total_amount: int
    currency: str


@dataclass
class GetOrderUseCase:
    uow: UnitOfWork

    async def __call__(self, order_id: int) -> GetOrderOutput:
        async with self.uow:
            order = await self.uow.orders.get(OrderId(order_id))
            if order is None:
                raise OrderNotFound(f"unknown order: {order_id}")

            return GetOrderOutput(
                order_id=order.id.value,
                user_id=order.user_id.value,
                status=order.status,
                lines=[
                    OrderLineDTO(
                        sku=line.sku.value,
                        quantity=line.quantity.value,
                        unit_amount=line.unit_price.amount,
                    )
                    for line in order.lines
                ],
                total_amount=order.total().amount,
                currency=order.total().currency,
            )
