"""/v1/orders — _구식_, deprecation 헤더 자동.

학습 의도: v2 와 _다른 모양_ 의 응답 (item vs sku) 을 _같은 도메인 모델_ 로 처리.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi_common import ApiEnvelope, success

from tender.auth import get_current_user
from tender.errors import OrderOutOfStockError
from tender.models import User
from tender.schemas import OrderCreateV1, OrderOutV1
from tender.uow import UnitOfWork


async def _add_deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 31 Dec 2026 23:59:59 GMT"
    response.headers["Link"] = '</v2/orders>; rel="successor-version"'


router = APIRouter(
    prefix="/v1/orders",
    tags=["orders v1 (deprecated)"],
    dependencies=[Depends(_add_deprecation_headers)],
)


_OUT_OF_STOCK = {"Discontinued"}


@router.post("", response_model=ApiEnvelope[OrderOutV1], status_code=201)
async def create_order(
    request: Request,
    payload: OrderCreateV1,
    current: Annotated[User, Depends(get_current_user)],
) -> ApiEnvelope[OrderOutV1]:
    """v1 입력은 `item` 자유 텍스트 — 내부에선 sku 로 통일 (대문자 + 하이픈)."""
    if payload.item in _OUT_OF_STOCK:
        raise OrderOutOfStockError(payload.item)

    sku_normalized = payload.item.upper().replace(" ", "-")[:30]

    sm = request.app.state.sessionmaker
    async with UnitOfWork(sm) as uow:
        order = await uow.orders.add(
            user_id=current.id, sku=sku_normalized, quantity=payload.quantity
        )
        await uow.outbox.record(
            topic="orders.created",
            key=str(order.id),
            payload={"order_id": order.id, "sku": order.sku, "quantity": order.quantity},
        )

    # v1 응답은 _원본 item_ 으로 (역호환)
    return success(OrderOutV1(id=order.id, item=payload.item, quantity=order.quantity))
