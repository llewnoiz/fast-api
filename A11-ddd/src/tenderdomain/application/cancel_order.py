"""CancelOrder Use Case."""

from __future__ import annotations

from dataclasses import dataclass

from tenderdomain.domain.exceptions import OrderNotFound
from tenderdomain.domain.value_objects import OrderId
from tenderdomain.ports.notifier import Notifier
from tenderdomain.ports.uow import UnitOfWork


@dataclass(frozen=True)
class CancelOrderInput:
    order_id: int
    reason: str


@dataclass
class CancelOrderUseCase:
    uow: UnitOfWork
    notifier: Notifier

    async def __call__(self, input: CancelOrderInput) -> None:
        async with self.uow:
            order = await self.uow.orders.get(OrderId(input.order_id))
            if order is None:
                raise OrderNotFound(f"unknown order: {input.order_id}")

            order.cancel(input.reason)  # 도메인 메서드 — 상태 머신 검증은 _도메인 책임_
            await self.uow.orders.save(order)
            events = order.pull_events()

        for event in events:
            await self.notifier.publish(event)
