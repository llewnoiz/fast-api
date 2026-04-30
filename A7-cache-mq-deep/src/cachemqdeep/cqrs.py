"""CQRS — Command Query Responsibility Segregation.

핵심 아이디어:
    _쓰기 모델_ 과 _읽기 모델_ 을 분리. 같은 데이터를 두 가지 표현으로 운영.

**왜?**
    - 읽기와 쓰기의 _패턴_ / _스케일_ / _일관성 요구_ 가 다름:
        쓰기 — 정규화 / 트랜잭션 / 도메인 무결성
        읽기 — 비정규화 / 캐시 / 다양한 뷰 (검색, 대시보드, 모바일)
    - 단일 모델로 둘 다 만족하려면 _복잡한 ORM 트릭_ 필요.

**현실 단계**:
    1. 같은 DB, 다른 _뷰_ (DB View / Materialized View)
    2. 같은 DB, 다른 _테이블_ (write 트리거 또는 outbox 로 read 모델 갱신)
    3. _다른 DB_ ── write=Postgres, read=Elasticsearch / DynamoDB
    4. **CQRS + Event Sourcing** (다음 모듈) — write 는 이벤트만, read 는 projection

**언제 쓰지 말기**:
    - CRUD 단순 앱 — _과한 복잡도_. 90% 의 앱은 단일 모델로 충분.
    - 팀 < 5명 / 서비스 < 5개 — 운영 부담 ↑↑.

본 모듈:
    - `Command` / `Query` / `CommandHandler` / `QueryHandler` 추상
    - 인메모리 _쓰기 저장소_ + 별도 _읽기 모델_ (비정규화)
    - command 가 read model 을 _직접_ 갱신 (단순화 — 운영은 이벤트 / outbox)

비교:
    Spring + Axon — `@CommandHandler` / `@QueryHandler` annotation
    .NET MediatR — Command/Query 분리 라이브러리
    Java Akka — Actor 기반 (메시지 패싱)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Order:
    """쓰기 모델 — 정규화. 도메인 불변식 보호."""

    id: int
    user_id: int
    item: str
    quantity: int
    status: str = "PENDING"


@dataclass
class OrderSummaryView:
    """읽기 모델 — 비정규화. _대시보드_ 용 사전 집계."""

    user_id: int
    total_orders: int = 0
    total_quantity: int = 0
    last_item: str = ""


@dataclass
class CreateOrderCommand:
    user_id: int
    item: str
    quantity: int


@dataclass
class GetUserSummaryQuery:
    user_id: int


@dataclass
class CqrsStore:
    """학습용 인메모리 — 쓰기 / 읽기 _분리_."""

    orders: dict[int, Order] = field(default_factory=dict)
    summaries: dict[int, OrderSummaryView] = field(default_factory=dict)
    _next_id: int = 1

    def next_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid


async def handle_create_order(store: CqrsStore, cmd: CreateOrderCommand) -> int:
    """Command 핸들러 — 쓰기 모델에 _기록_ + 읽기 모델 _갱신_.

    학습 단순화: 같은 트랜잭션에서 두 모델 모두 갱신. 운영은 _outbox 이벤트_ 로 분리해
    eventual consistency. 12-13 단계의 outbox / Kafka 패턴이 이 자리에 들어감.
    """
    order = Order(
        id=store.next_id(),
        user_id=cmd.user_id,
        item=cmd.item,
        quantity=cmd.quantity,
        status="PENDING",
    )
    store.orders[order.id] = order

    summary = store.summaries.setdefault(
        cmd.user_id, OrderSummaryView(user_id=cmd.user_id)
    )
    summary.total_orders += 1
    summary.total_quantity += cmd.quantity
    summary.last_item = cmd.item
    return order.id


async def handle_get_summary(
    store: CqrsStore, query: GetUserSummaryQuery
) -> OrderSummaryView | None:
    """Query 핸들러 — 읽기 모델에서 _바로_ 가져옴. JOIN / 집계 없음."""
    return store.summaries.get(query.user_id)


# ─────────────────────────────────────────────────────────────────
# Mediator 스타일 (선택) ── handler 등록 → dispatch
# ─────────────────────────────────────────────────────────────────


class Mediator:
    """`MediatR` 스타일 — Command/Query 타입 → handler 매핑."""

    def __init__(self) -> None:
        self._handlers: dict[type, Callable[[Any], Awaitable[Any]]] = {}

    def register(self, msg_type: type, handler: Callable[[Any], Awaitable[Any]]) -> None:
        self._handlers[msg_type] = handler

    async def send(self, message: Any) -> Any:
        handler = self._handlers.get(type(message))
        if handler is None:
            raise KeyError(f"no handler for {type(message).__name__}")
        return await handler(message)
