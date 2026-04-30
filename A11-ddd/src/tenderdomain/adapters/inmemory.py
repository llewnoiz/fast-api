"""인메모리 어댑터 — 학습 / 테스트 친화. 운영은 SQLAlchemy + Postgres.

핵심: _도메인은 그대로_, 어댑터만 교체. 헥사고날의 약속.

비교:
    Spring 의 `@Repository` JPA 구현 vs in-memory test stub
    NestJS `Injectable` 토큰 교체 (production vs test)
"""

from __future__ import annotations

from types import TracebackType

from tenderdomain.domain.events import DomainEvent
from tenderdomain.domain.order import Order
from tenderdomain.domain.value_objects import OrderId, UserId
from tenderdomain.ports.notifier import Notifier
from tenderdomain.ports.repositories import OrderRepository, UserRepository
from tenderdomain.ports.uow import UnitOfWork


class InMemoryOrderRepository:
    """OrderRepository Protocol 구현. dict 기반 저장."""

    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}

    async def add(self, order: Order) -> None:
        if order.id.value in self._orders:
            raise ValueError(f"duplicate order id: {order.id.value}")
        self._orders[order.id.value] = order

    async def get(self, order_id: OrderId) -> Order | None:
        return self._orders.get(order_id.value)

    async def list_by_user(self, user_id: UserId) -> list[Order]:
        return [o for o in self._orders.values() if o.user_id == user_id]

    async def save(self, order: Order) -> None:
        self._orders[order.id.value] = order


class InMemoryUserRepository:
    def __init__(self, user_ids: set[int] | None = None) -> None:
        self._users: set[int] = user_ids if user_ids is not None else set()

    def add(self, user_id: int) -> None:
        self._users.add(user_id)

    async def exists(self, user_id: UserId) -> bool:
        return user_id.value in self._users


class CollectingNotifier:
    """이벤트를 _리스트에 모음_ ── 테스트가 `notifier.events` 로 검증."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


class InMemoryUnitOfWork:
    """간이 UoW.

    _commit / rollback_ 은 인메모리에선 의미 약함 (저장이 곧 메모리 변경).
    학습 의도: _Protocol_ 패턴 + Aggregate 의 _이벤트 영속 시점_ 명확히.

    실제 트랜잭션 시뮬: `_committed` 플래그로 with 블록 _밖_ 에서 변경이 보이는지 검증 가능.
    """

    def __init__(
        self,
        orders: OrderRepository | None = None,
        users: UserRepository | None = None,
    ) -> None:
        self.orders: OrderRepository = orders or InMemoryOrderRepository()
        self.users: UserRepository = users or InMemoryUserRepository()
        self._entered: bool = False
        self._committed: bool = False
        self._rolled_back: bool = False

    async def __aenter__(self) -> InMemoryUnitOfWork:
        self._entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True


# 어댑터가 Notifier Protocol 을 _만족_ 하는지 mypy 체크용 — 학습 표시
_check_notifier: Notifier = CollectingNotifier()
_check_uow: UnitOfWork = InMemoryUnitOfWork()
