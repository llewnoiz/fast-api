"""/v1/orders — _구식_ 버전. v2 가 후속자.

공통 패턴:
    - 응답은 항상 `ApiEnvelope[OrderOutV1]`
    - 에러는 `raise OrderNotFoundError(...)` — 핸들러가 envelope 으로 변환
    - 모든 엔드포인트에 deprecation 헤더 (라우터 _전체_ dependencies)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from errver.api.deprecation import add_deprecation_headers
from errver.envelope import ApiEnvelope, success
from errver.errors import OrderNotFoundError, OrderOutOfStockError

router = APIRouter(
    prefix="/v1/orders",
    tags=["orders v1 (deprecated)"],
    dependencies=[Depends(add_deprecation_headers("/v2/orders"))],
)


class OrderOutV1(BaseModel):
    id: int
    item: str
    quantity: int


class OrderCreateV1(BaseModel):
    item: str = Field(min_length=1, max_length=50, examples=["Pencil"])
    quantity: int = Field(gt=0, le=100, examples=[2])


# 학습용 인메모리 저장소
_DB: dict[int, OrderOutV1] = {
    1: OrderOutV1(id=1, item="Pencil", quantity=2),
}
_OUT_OF_STOCK = {"DISCONTINUED-001"}   # 가짜 재고 정책


@router.get(
    "/{order_id}",
    response_model=ApiEnvelope[OrderOutV1],
    summary="단일 주문 조회 (v1, deprecated)",
)
async def get_order(order_id: int) -> ApiEnvelope[OrderOutV1]:
    order = _DB.get(order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return success(order)


@router.post(
    "",
    response_model=ApiEnvelope[OrderOutV1],
    status_code=status.HTTP_201_CREATED,
    summary="주문 생성 (v1, deprecated)",
)
async def create_order(payload: OrderCreateV1) -> ApiEnvelope[OrderOutV1]:
    if payload.item in _OUT_OF_STOCK:
        raise OrderOutOfStockError(payload.item)

    new_id = max(_DB.keys(), default=0) + 1
    order = OrderOutV1(id=new_id, item=payload.item, quantity=payload.quantity)
    _DB[new_id] = order
    return success(order, message="created")
