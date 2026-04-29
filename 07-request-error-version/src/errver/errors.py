"""에러 코드 표준화 + 도메인 예외.

비교:
    Spring:    @ControllerAdvice + ExceptionHandler + 커스텀 예외 트리
    NestJS:    HttpException 상속 + ExceptionFilter
    Go:        errors.Is / errors.As 패턴 (구조 다름)

규칙:
    - **HTTP status 와 도메인 에러 코드를 _분리_**:
        404 + "ORDER_NOT_FOUND"
        404 + "USER_NOT_FOUND"
        같은 status 도 _도메인 코드_ 가 다르면 클라가 _다르게_ 처리 가능
    - 에러 코드는 _불변_ — 클라이언트 코드와 _계약_. 함부로 바꾸지 말 것.
    - 메시지는 _바뀔 수 있음_ (다국어, 표현 개선) — 클라가 _코드 기반_ 으로 분기하도록.

다국어 메시지는 부록 A1 (i18n) 에서. 여기선 한국어/영어 단일.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """모든 도메인 에러 코드 _카탈로그_. 새로 추가 가능, 삭제·이름 변경은 _깨짐 변경_.

    `StrEnum` (3.11+) — `str` + `Enum` 의 표준 후계자. 이전 코드의 `class X(str, Enum)`
    패턴이 metaclass 충돌 가능성 있어 권장 안 됨.
    """

    # 일반
    VALIDATION = "VALIDATION_ERROR"
    INTERNAL = "INTERNAL_ERROR"

    # 인증/인가 (09 단계 떡밥)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # 리소스
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"

    # 도메인 — 주문
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_OUT_OF_STOCK = "ORDER_OUT_OF_STOCK"


class DomainError(Exception):
    """도메인 예외의 _베이스_. 라우트에서 `raise OrderNotFoundError(123)` 하면
    전역 핸들러가 envelope 응답으로 변환.

    `status` = HTTP 응답 코드, `code` = 클라가 분기에 쓰는 도메인 코드.
    """

    def __init__(self, *, code: ErrorCode, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


# ============================================================================
# 도메인별 구체 예외
# ============================================================================


class OrderNotFoundError(DomainError):
    def __init__(self, order_id: int | str) -> None:
        super().__init__(
            code=ErrorCode.ORDER_NOT_FOUND,
            message=f"order {order_id} not found",
            status=404,
        )


class OrderOutOfStockError(DomainError):
    def __init__(self, sku: str) -> None:
        super().__init__(
            code=ErrorCode.ORDER_OUT_OF_STOCK,
            message=f"sku {sku!r} is out of stock",
            status=409,
        )
