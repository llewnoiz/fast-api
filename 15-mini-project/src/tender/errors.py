"""tender 도메인 예외 — fastapi-common 의 DomainError 베이스 활용."""

from __future__ import annotations

from fastapi_common import DomainError, ErrorCode


class TenderErrorCode:
    """앱별 _확장_ 에러 코드. fastapi-common 의 ErrorCode 와 _공존_."""

    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_OUT_OF_STOCK = "ORDER_OUT_OF_STOCK"
    USER_NOT_FOUND = "USER_NOT_FOUND"


class OrderNotFoundError(DomainError):
    def __init__(self, order_id: int) -> None:
        super().__init__(
            code=TenderErrorCode.ORDER_NOT_FOUND,
            message=f"order {order_id} not found",
            status=404,
        )


class OrderOutOfStockError(DomainError):
    def __init__(self, sku: str) -> None:
        super().__init__(
            code=TenderErrorCode.ORDER_OUT_OF_STOCK,
            message=f"sku {sku!r} is out of stock",
            status=409,
        )


class AuthError(DomainError):
    def __init__(self, message: str = "인증 실패") -> None:
        super().__init__(code=ErrorCode.UNAUTHORIZED, message=message, status=401)
