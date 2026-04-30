"""FastAPI 라우터 — 어댑터 layer 의 _하나_. CLI / GraphQL 도 같은 use case 재사용 가능.

규칙:
    - 라우터는 _DTO ↔ Pydantic_ 변환만 + use case 호출.
    - 도메인 객체 _직접 노출 X_ ── Pydantic 응답 모델로 변환.
    - 도메인 예외 → HTTP 상태 코드 매핑.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from tenderdomain.application.cancel_order import CancelOrderInput, CancelOrderUseCase
from tenderdomain.application.get_order import GetOrderUseCase
from tenderdomain.application.place_order import PlaceOrderInput, PlaceOrderUseCase
from tenderdomain.domain.exceptions import (
    DomainError,
    IllegalStateTransition,
    InvariantViolation,
    OrderNotFound,
    UserNotFound,
)


class OrderLineIn(BaseModel):
    sku: str = Field(min_length=8, max_length=8)
    quantity: int = Field(ge=1, le=1000)
    unit_amount: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class PlaceOrderRequest(BaseModel):
    user_id: int
    lines: list[OrderLineIn]


class OrderLineOut(BaseModel):
    sku: str
    quantity: int
    unit_amount: int


class OrderResponse(BaseModel):
    order_id: int
    user_id: int
    status: str
    lines: list[OrderLineOut]
    total_amount: int
    currency: str


class CancelRequest(BaseModel):
    reason: str


def _domain_exc_to_http(exc: DomainError) -> HTTPException:
    """도메인 예외 → HTTP 코드 매핑. 어댑터 책임 — 도메인은 HTTP 모름."""
    if isinstance(exc, OrderNotFound | UserNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, InvariantViolation):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, IllegalStateTransition):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _get_place(request: Request) -> PlaceOrderUseCase:
    place: PlaceOrderUseCase = request.app.state.place_order_uc
    return place


def _get_cancel(request: Request) -> CancelOrderUseCase:
    cancel: CancelOrderUseCase = request.app.state.cancel_order_uc
    return cancel


def _get_query(request: Request) -> GetOrderUseCase:
    get: GetOrderUseCase = request.app.state.get_order_uc
    return get


PlaceDep = Annotated[PlaceOrderUseCase, Depends(_get_place)]
CancelDep = Annotated[CancelOrderUseCase, Depends(_get_cancel)]
QueryDep = Annotated[GetOrderUseCase, Depends(_get_query)]


def make_router() -> APIRouter:
    router = APIRouter(prefix="/orders", tags=["orders"])

    @router.post("", status_code=201)
    async def place_order(payload: PlaceOrderRequest, place: PlaceDep) -> dict[str, int | str]:
        try:
            result = await place(
                PlaceOrderInput(
                    user_id=payload.user_id,
                    lines=[
                        (line.sku, line.quantity, line.unit_amount, line.currency)
                        for line in payload.lines
                    ],
                )
            )
        except DomainError as e:
            raise _domain_exc_to_http(e) from e
        return {
            "order_id": result.order_id,
            "total_amount": result.total_amount,
            "currency": result.currency,
            "line_count": result.line_count,
        }

    @router.get("/{order_id}", response_model=OrderResponse)
    async def get_order(order_id: int, query: QueryDep) -> OrderResponse:
        try:
            out = await query(order_id)
        except DomainError as e:
            raise _domain_exc_to_http(e) from e
        return OrderResponse(
            order_id=out.order_id,
            user_id=out.user_id,
            status=out.status.value,
            lines=[
                OrderLineOut(sku=line.sku, quantity=line.quantity, unit_amount=line.unit_amount)
                for line in out.lines
            ],
            total_amount=out.total_amount,
            currency=out.currency,
        )

    @router.post("/{order_id}/cancel", status_code=204)
    async def cancel_order(order_id: int, payload: CancelRequest, cancel: CancelDep) -> None:
        try:
            await cancel(CancelOrderInput(order_id=order_id, reason=payload.reason))
        except DomainError as e:
            raise _domain_exc_to_http(e) from e

    return router
