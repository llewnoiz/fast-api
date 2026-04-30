"""Domain Events — _과거에 일어난 일_ (이름은 _과거형_).

규칙:
    - 불변, 데이터만 (행동 X)
    - _과거 시제_: `OrderPlaced`, `OrderCancelled` (`PlaceOrder`, `CancelOrder` 는 _Command_)
    - 발행자 (Aggregate) 가 자기 변경 후 `record_event` — _저장 시점_ 에 인프라가 발행
    - 영속성 트랜잭션 _내_ 에서 outbox 에 기록 — at-least-once 보장 (13 단계 outbox 패턴)

비교:
    Spring `@EventListener` + `ApplicationEventPublisher`
    Axon Framework Domain Event
    Node `EventEmitter` (단, _영속_ X)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from tenderdomain.domain.value_objects import Money, OrderId, UserId


@dataclass(frozen=True)
class DomainEvent:
    """모든 이벤트의 베이스. `name` 은 직렬화 시 type 식별자."""

    name: ClassVar[str] = "DomainEvent"
    occurred_at: datetime


@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    name: ClassVar[str] = "OrderPlaced"
    order_id: OrderId
    user_id: UserId
    total: Money

    @classmethod
    def now(cls, *, order_id: OrderId, user_id: UserId, total: Money) -> OrderPlaced:
        return cls(occurred_at=datetime.now(UTC), order_id=order_id, user_id=user_id, total=total)


@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    name: ClassVar[str] = "OrderCancelled"
    order_id: OrderId
    reason: str

    @classmethod
    def now(cls, *, order_id: OrderId, reason: str) -> OrderCancelled:
        return cls(occurred_at=datetime.now(UTC), order_id=order_id, reason=reason)
