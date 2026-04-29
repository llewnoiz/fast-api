"""/v2/orders — _현재_ 버전.

v1 → v2 변경:
    - `item` (자유 텍스트) → `sku` (정형 SKU 코드)
    - `created_at` 추가 (UTC ISO 8601)
    - 에러 envelope 동일

마이그레이션 가이드는 README 참고.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from errver.envelope import ApiEnvelope, success
from errver.errors import OrderNotFoundError, OrderOutOfStockError

router = APIRouter(prefix="/v2/orders", tags=["orders v2"])


class OrderOutV2(BaseModel):
    id: int
    sku: str = Field(examples=["PEN-001"])
    quantity: int
    created_at: datetime


class OrderCreateV2(BaseModel):
    sku: str = Field(min_length=1, max_length=30, pattern=r"^[A-Z0-9-]+$",
                     examples=["PEN-001"], description="정형 SKU — 대문자/숫자/하이픈")
    quantity: int = Field(gt=0, le=100, examples=[2])


_DB: dict[int, OrderOutV2] = {
    1: OrderOutV2(id=1, sku="PEN-001", quantity=2, created_at=datetime(2026, 1, 1, tzinfo=UTC)),
}
_OUT_OF_STOCK = {"DISCONTINUED-001"}


@router.get(
    "/{order_id}",
    response_model=ApiEnvelope[OrderOutV2],
    summary="단일 주문 조회 (v2)",
    responses={
        404: {
            "description": "주문 없음",
            "content": {
                "application/json": {
                    "example": {"code": "ORDER_NOT_FOUND", "message": "order 999 not found", "data": None},
                },
            },
        },
    },
)
async def get_order(order_id: int) -> ApiEnvelope[OrderOutV2]:
    order = _DB.get(order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return success(order)


@router.post(
    "",
    response_model=ApiEnvelope[OrderOutV2],
    status_code=status.HTTP_201_CREATED,
    summary="주문 생성 (v2)",
    responses={
        409: {
            "description": "재고 없음",
            "content": {
                "application/json": {
                    "example": {"code": "ORDER_OUT_OF_STOCK", "message": "sku 'X' is out of stock", "data": None},
                },
            },
        },
    },
)
async def create_order(payload: OrderCreateV2) -> ApiEnvelope[OrderOutV2]:
    if payload.sku in _OUT_OF_STOCK:
        raise OrderOutOfStockError(payload.sku)

    new_id = max(_DB.keys(), default=0) + 1
    order = OrderOutV2(
        id=new_id,
        sku=payload.sku,
        quantity=payload.quantity,
        created_at=datetime.now(UTC),
    )
    _DB[new_id] = order
    return success(order, message="created")
