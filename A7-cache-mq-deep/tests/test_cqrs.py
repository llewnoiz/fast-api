"""CQRS 단위 테스트."""

from __future__ import annotations

from cachemqdeep.cqrs import (
    CqrsStore,
    CreateOrderCommand,
    GetUserSummaryQuery,
    Mediator,
    handle_create_order,
    handle_get_summary,
)


async def test_command_updates_both_models() -> None:
    store = CqrsStore()
    oid = await handle_create_order(store, CreateOrderCommand(1, "book", 2))
    assert oid == 1
    # 쓰기 모델
    assert store.orders[oid].quantity == 2
    # 읽기 모델 — 비정규화 합산
    summary = store.summaries[1]
    assert summary.total_orders == 1
    assert summary.total_quantity == 2


async def test_query_returns_summary() -> None:
    store = CqrsStore()
    await handle_create_order(store, CreateOrderCommand(7, "pen", 3))
    await handle_create_order(store, CreateOrderCommand(7, "pencil", 5))
    view = await handle_get_summary(store, GetUserSummaryQuery(7))
    assert view is not None
    assert view.total_orders == 2
    assert view.total_quantity == 8
    assert view.last_item == "pencil"


async def test_query_returns_none_for_unknown_user() -> None:
    store = CqrsStore()
    view = await handle_get_summary(store, GetUserSummaryQuery(99))
    assert view is None


async def test_mediator_dispatch() -> None:
    store = CqrsStore()
    mediator = Mediator()
    mediator.register(CreateOrderCommand, lambda c: handle_create_order(store, c))
    mediator.register(GetUserSummaryQuery, lambda q: handle_get_summary(store, q))

    await mediator.send(CreateOrderCommand(2, "tea", 1))
    view = await mediator.send(GetUserSummaryQuery(2))
    assert view.total_orders == 1
