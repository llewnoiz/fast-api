"""Order Aggregate — _불변식_ 보호의 _경계_.

DDD 핵심 개념:
    **Aggregate**: 함께 변하는 Entity + VO 의 _묶음_. _하나의 트랜잭션 단위_.
    **Aggregate Root**: 외부에서 _접근하는 유일한 진입점_. 내부 Entity 는 root 거치지 않으면 X.
    **Invariant** (불변식): 항상 참이어야 하는 비즈니스 규칙. Aggregate 가 _보호_.

본 Aggregate (Order):
    - Entity: Order (id 가 정체성)
    - 내부 컬렉션: OrderLine (Entity? VO? 학습용으론 VO 처럼 다룸)
    - 불변식:
        1. items 비어있으면 안 됨 (생성 시점)
        2. 같은 SKU 두 번 들어가면 _수량 합산_
        3. PLACED → PAID → SHIPPED → COMPLETED 또는 PLACED → CANCELLED
        4. 이미 결제된 주문은 취소 불가 (단순화 — 운영은 환불 워크플로)

Aggregate 설계 원칙:
    - **작게**: 한 트랜잭션 = 한 Aggregate. 너무 크면 락 경합 / consistency 압박.
    - **외부 참조는 ID 로**: Order 가 User 를 _참조_ 하면 `User` 객체 X, `UserId` (VO).
    - **Application Service** 가 여러 Aggregate _코디네이션_ — Aggregate 끼리 직접 호출 X.

비교:
    Spring + Axon — `@AggregateRoot`, `@AggregateMember`
    Java DDD 책 (Vaughn Vernon) ── 본 모듈의 패턴 그대로
    TypeScript: NestJS + tactical DDD 라이브러리 (NestJS-DDD)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from tenderdomain.domain.events import DomainEvent, OrderCancelled, OrderPlaced
from tenderdomain.domain.exceptions import IllegalStateTransition, InvariantViolation
from tenderdomain.domain.value_objects import SKU, Money, OrderId, Quantity, UserId


class OrderStatus(StrEnum):
    PLACED = "PLACED"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class OrderLine:
    """주문 항목 — VO 처럼 불변. 합산 시 _새 인스턴스_."""

    sku: SKU
    quantity: Quantity
    unit_price: Money

    def subtotal(self) -> Money:
        return self.unit_price.multiply(self.quantity.value)

    def add_quantity(self, more: Quantity) -> OrderLine:
        return OrderLine(
            sku=self.sku,
            quantity=Quantity(self.quantity.value + more.value),
            unit_price=self.unit_price,
        )


@dataclass
class Order:
    """Aggregate Root. _public 메서드만_ 외부 노출 — 직접 필드 변경 X.

    `events` 는 _발생한 도메인 이벤트_ 누적. UoW 가 commit 시 publish.
    """

    id: OrderId
    user_id: UserId
    lines: list[OrderLine]
    status: OrderStatus = OrderStatus.PLACED
    events: list[DomainEvent] = field(default_factory=list)

    # ─────────────────────────────────────────────────────────────
    # 생성자 (factory) ── 불변식 검사 + OrderPlaced 이벤트
    # ─────────────────────────────────────────────────────────────
    @classmethod
    def place(
        cls,
        *,
        order_id: OrderId,
        user_id: UserId,
        lines: list[OrderLine],
    ) -> Order:
        if not lines:
            raise InvariantViolation("order must have at least 1 line")
        merged = cls._merge_same_sku(lines)
        order = cls(id=order_id, user_id=user_id, lines=merged, status=OrderStatus.PLACED)
        order.events.append(
            OrderPlaced.now(order_id=order_id, user_id=user_id, total=order.total())
        )
        return order

    @staticmethod
    def _merge_same_sku(lines: list[OrderLine]) -> list[OrderLine]:
        merged: dict[SKU, OrderLine] = {}
        for line in lines:
            existing = merged.get(line.sku)
            merged[line.sku] = existing.add_quantity(line.quantity) if existing else line
        return list(merged.values())

    # ─────────────────────────────────────────────────────────────
    # 행동 (commands)
    # ─────────────────────────────────────────────────────────────
    def pay(self) -> None:
        self._require_status(OrderStatus.PLACED, action="pay")
        self.status = OrderStatus.PAID

    def ship(self) -> None:
        self._require_status(OrderStatus.PAID, action="ship")
        self.status = OrderStatus.SHIPPED

    def complete(self) -> None:
        self._require_status(OrderStatus.SHIPPED, action="complete")
        self.status = OrderStatus.COMPLETED

    def cancel(self, reason: str) -> None:
        if self.status in (OrderStatus.SHIPPED, OrderStatus.COMPLETED):
            raise IllegalStateTransition(
                f"cannot cancel order in status {self.status}: must refund instead"
            )
        if self.status == OrderStatus.CANCELLED:
            raise IllegalStateTransition("already cancelled")
        self.status = OrderStatus.CANCELLED
        self.events.append(OrderCancelled.now(order_id=self.id, reason=reason))

    # ─────────────────────────────────────────────────────────────
    # 조회 (queries)
    # ─────────────────────────────────────────────────────────────
    def total(self) -> Money:
        if not self.lines:
            raise InvariantViolation("empty order has no total")
        result = self.lines[0].subtotal()
        for line in self.lines[1:]:
            result = result.add(line.subtotal())
        return result

    def line_count(self) -> int:
        return len(self.lines)

    def pull_events(self) -> list[DomainEvent]:
        """이벤트 _꺼내서 비움_ — UoW 가 publish 후 호출."""
        events = list(self.events)
        self.events.clear()
        return events

    # ─────────────────────────────────────────────────────────────
    # 내부 헬퍼
    # ─────────────────────────────────────────────────────────────
    def _require_status(self, expected: OrderStatus, *, action: str) -> None:
        if self.status != expected:
            raise IllegalStateTransition(
                f"cannot {action}: order is {self.status}, expected {expected}"
            )
