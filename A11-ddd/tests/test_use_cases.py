"""Use Case (Application Service) 통합 테스트 — _인메모리 어댑터_ 사용.

도메인 + 어댑터 _연결_ 검증. 운영 어댑터 (SQLAlchemy / Kafka) 는 별도 테스트.
"""

from __future__ import annotations

import pytest
from tenderdomain.adapters.inmemory import (
    CollectingNotifier,
    InMemoryUnitOfWork,
)
from tenderdomain.application.cancel_order import CancelOrderInput, CancelOrderUseCase
from tenderdomain.application.get_order import GetOrderUseCase
from tenderdomain.application.place_order import PlaceOrderInput, PlaceOrderUseCase
from tenderdomain.domain.events import OrderCancelled, OrderPlaced
from tenderdomain.domain.exceptions import OrderNotFound, UserNotFound


async def test_place_order_happy_path(
    uow: InMemoryUnitOfWork, notifier: CollectingNotifier
) -> None:
    place = PlaceOrderUseCase(uow=uow, notifier=notifier)
    out = await place(
        PlaceOrderInput(user_id=1, lines=[("ABC-0001", 2, 1000, "KRW")])
    )
    assert out.order_id == 1
    assert out.total_amount == 2000
    assert out.line_count == 1
    # 이벤트 _commit 후_ publish 확인
    assert len(notifier.events) == 1
    assert isinstance(notifier.events[0], OrderPlaced)


async def test_place_order_unknown_user_404(
    uow: InMemoryUnitOfWork, notifier: CollectingNotifier
) -> None:
    place = PlaceOrderUseCase(uow=uow, notifier=notifier)
    with pytest.raises(UserNotFound):
        await place(
            PlaceOrderInput(user_id=99, lines=[("ABC-0001", 1, 1000, "KRW")])
        )


async def test_place_order_unknown_user_publishes_no_events(
    uow: InMemoryUnitOfWork, notifier: CollectingNotifier
) -> None:
    """commit 실패 → 이벤트 publish X. 트랜잭션 일관성."""
    place = PlaceOrderUseCase(uow=uow, notifier=notifier)
    with pytest.raises(UserNotFound):
        await place(
            PlaceOrderInput(user_id=99, lines=[("ABC-0001", 1, 1000, "KRW")])
        )
    assert notifier.events == []


async def test_cancel_then_get_returns_cancelled(
    uow: InMemoryUnitOfWork, notifier: CollectingNotifier
) -> None:
    place = PlaceOrderUseCase(uow=uow, notifier=notifier)
    cancel = CancelOrderUseCase(uow=uow, notifier=notifier)
    query = GetOrderUseCase(uow=uow)

    out = await place(
        PlaceOrderInput(user_id=1, lines=[("ABC-0001", 1, 500, "KRW")])
    )
    await cancel(CancelOrderInput(order_id=out.order_id, reason="test"))

    detail = await query(out.order_id)
    assert detail.status.value == "CANCELLED"
    # OrderPlaced + OrderCancelled
    cancelled = [e for e in notifier.events if isinstance(e, OrderCancelled)]
    assert len(cancelled) == 1


async def test_get_unknown_order_raises(uow: InMemoryUnitOfWork) -> None:
    query = GetOrderUseCase(uow=uow)
    with pytest.raises(OrderNotFound):
        await query(999)


async def test_uow_commit_called_on_success(
    uow: InMemoryUnitOfWork, notifier: CollectingNotifier
) -> None:
    place = PlaceOrderUseCase(uow=uow, notifier=notifier)
    await place(PlaceOrderInput(user_id=1, lines=[("ABC-0001", 1, 100, "KRW")]))
    assert uow._committed is True
    assert uow._rolled_back is False


async def test_uow_rollback_on_failure(
    uow: InMemoryUnitOfWork, notifier: CollectingNotifier
) -> None:
    place = PlaceOrderUseCase(uow=uow, notifier=notifier)
    with pytest.raises(UserNotFound):
        await place(PlaceOrderInput(user_id=99, lines=[("ABC-0001", 1, 100, "KRW")]))
    assert uow._rolled_back is True
    assert uow._committed is False
