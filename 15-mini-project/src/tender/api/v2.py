"""/v2/orders — 현재 버전. 인증 필요 + cache + outbox 통합."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi_common import ApiEnvelope, success

from tender.auth import get_current_user
from tender.cache import OrderCache
from tender.errors import OrderOutOfStockError
from tender.models import User
from tender.schemas import OrderCreateV2, OrderOutV2
from tender.uow import UnitOfWork

router = APIRouter(prefix="/v2/orders", tags=["orders v2"])


_OUT_OF_STOCK = {"DISCONTINUED-001"}


def _to_out(order) -> OrderOutV2:  # noqa: ANN001
    return OrderOutV2(
        id=order.id, sku=order.sku, quantity=order.quantity,
        status=order.status, created_at=order.created_at,
    )


@router.post("", response_model=ApiEnvelope[OrderOutV2], status_code=201)
async def create_order(
    request: Request,
    payload: OrderCreateV2,
    current: Annotated[User, Depends(get_current_user)],
) -> ApiEnvelope[OrderOutV2]:
    """주문 생성:
    1. DB 트랜잭션 안에서 Order 생성 + outbox 이벤트 기록 (원자성)
    2. 트랜잭션 commit 후 사용자별 캐시 무효화
    """
    if payload.sku in _OUT_OF_STOCK:
        raise OrderOutOfStockError(payload.sku)

    sm = request.app.state.sessionmaker
    async with UnitOfWork(sm) as uow:
        order = await uow.orders.add(
            user_id=current.id, sku=payload.sku, quantity=payload.quantity
        )
        # outbox 패턴 — 같은 트랜잭션. 별도 워커가 Kafka 로 relay
        await uow.outbox.record(
            topic="orders.created",
            key=str(order.id),
            payload={"order_id": order.id, "sku": order.sku, "quantity": order.quantity},
        )
        # 트랜잭션 commit 은 with 블록 끝에서 자동
        order_dict = {"id": order.id, "sku": order.sku, "quantity": order.quantity}
        order_dict["status"] = order.status
        order_dict["created_at"] = order.created_at

    # 캐시 무효화 (트랜잭션 commit 후)
    cache: OrderCache = request.app.state.cache
    await cache.invalidate_user_orders(current.id)

    return success(_to_out(order))


@router.get("/{order_id}", response_model=ApiEnvelope[OrderOutV2])
async def get_order(
    request: Request,
    order_id: int,
    current: Annotated[User, Depends(get_current_user)],
) -> ApiEnvelope[OrderOutV2]:
    """단일 조회 — cache-aside.

    1) cache.get → hit 면 그대로
    2) miss → DB 조회 → cache.set → 반환
    """
    cache: OrderCache = request.app.state.cache
    cached = await cache.get_order(order_id)
    if cached is not None:
        return success(OrderOutV2.model_validate(cached))

    sm = request.app.state.sessionmaker
    async with UnitOfWork(sm) as uow:
        order = await uow.orders.get(order_id)
        out = _to_out(order)

    await cache.set_order(order_id, out.model_dump(mode="json"))
    return success(out)
