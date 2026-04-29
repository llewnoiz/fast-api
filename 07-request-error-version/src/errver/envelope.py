"""공통 응답 envelope.

비교:
    NestJS:      ResponseInterceptor (ClassSerializerInterceptor) 로 일관된 응답 포장
    Spring:      `ResponseEntity<ApiResponse<T>>` + `@RestControllerAdvice`
    Stripe API:  사실은 envelope 없이 _리소스_ 자체 + 에러는 별도 형태 (미니멀)
    GitHub API:  envelope 없음, 에러는 message+errors 필드

표준 _RFC 7807 Problem Details_ 도 있음 (`application/problem+json`):
    { "type": "https://...", "title": "...", "status": 404, "detail": "...", "instance": "..." }
이건 _에러 응답 한정_ 표준. 우리 envelope 는 _성공/실패 둘 다_ 같은 모양.

선택은 도메인/팀 컨벤션. 본 학습은 단순 `{code, message, data}` envelope.

PEP 695 제네릭으로 `class ApiEnvelope[T]:` 작성. Pydantic v2 가 지원.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ApiEnvelope[T](BaseModel):
    """모든 응답을 감싸는 공통 형태 — PEP 695 제네릭.

    OpenAPI 에 _제네릭으로 노출_ 되어 라우트마다 `data` 의 실제 타입이 보임.
    """

    code: str = Field(description="기계가 판독하는 코드 (예: OK, NOT_FOUND)")
    message: str = Field(description="사람이 읽는 메시지 — 에러 시 사용자에게 보일 수도")
    data: T | None = Field(default=None, description="실제 페이로드 (성공 시 채워짐)")


def success[T](data: T, message: str = "ok") -> ApiEnvelope[T]:
    return ApiEnvelope[T](code="OK", message=message, data=data)
