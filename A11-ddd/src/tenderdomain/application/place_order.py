"""PlaceOrder Use Case — Application Service.

규칙:
    - **얇은 layer** ── 입력 검증, UoW 시작, Aggregate 메서드 호출, 결과 반환만.
    - 비즈니스 _법칙_ 은 도메인에 (Aggregate / Domain Service / VO).
    - 여러 Aggregate 의 _코디네이션_ 만 여기서.
    - DTO (Input/Output) 로 _도메인 객체 노출 X_ — 어댑터 (HTTP / GraphQL / CLI) 가 변환.

비교:
    Spring `@Service` 클래스의 메서드 — 트랜잭션 시작 + 도메인 호출
    NestJS Service
    Clean Architecture 의 _Use Case Interactor_
"""

from __future__ import annotations

from dataclasses import dataclass

from tenderdomain.domain.exceptions import UserNotFound
from tenderdomain.domain.order import Order, OrderLine
from tenderdomain.domain.value_objects import SKU, Money, OrderId, Quantity, UserId
from tenderdomain.ports.notifier import Notifier
from tenderdomain.ports.uow import UnitOfWork


@dataclass(frozen=True)
class PlaceOrderInput:
    user_id: int
    lines: list[tuple[str, int, int, str]]  # (sku, quantity, unit_amount, currency)


@dataclass(frozen=True)
class PlaceOrderOutput:
    order_id: int
    total_amount: int
    currency: str
    line_count: int


@dataclass
class PlaceOrderUseCase:
    """`async def __call__` — Spring 의 service method 와 같은 위치."""

    uow: UnitOfWork
    notifier: Notifier
    next_order_id: int = 1

    def _allocate_id(self) -> OrderId:
        oid = OrderId(self.next_order_id)
        self.next_order_id += 1
        return oid

    async def __call__(self, input: PlaceOrderInput) -> PlaceOrderOutput:
        async with self.uow:
            user_id = UserId(input.user_id)
            if not await self.uow.users.exists(user_id):
                raise UserNotFound(f"unknown user: {input.user_id}")

            lines = [
                OrderLine(
                    sku=SKU(sku),
                    quantity=Quantity(qty),
                    unit_price=Money(unit_amount, currency),
                )
                for sku, qty, unit_amount, currency in input.lines
            ]

            order = Order.place(
                order_id=self._allocate_id(),
                user_id=user_id,
                lines=lines,
            )
            await self.uow.orders.add(order)

            # commit 후 _이벤트 publish_ — 트랜잭션 일관성 보장.
            # `__aexit__` 에서 commit 실행 후 이 블록 종료.
            events = order.pull_events()

        # commit 성공한 경우에만 도달 — 실패면 with 가 raise
        for event in events:
            await self.notifier.publish(event)

        return PlaceOrderOutput(
            order_id=order.id.value,
            total_amount=order.total().amount,
            currency=order.total().currency,
            line_count=order.line_count(),
        )
