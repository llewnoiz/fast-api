"""ApiEnvelope[T] — 모든 응답의 공통 형태.

규칙:
    - 모든 라우트가 `ApiEnvelope[T]` 반환 (예외: `/healthz` Docker HEALTHCHECK 단순성)
    - 모든 에러도 envelope (전역 핸들러가 처리)
    - 변경 시 _깨짐 변경_ ── 클라이언트 SDK 영향
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ApiEnvelope[T](BaseModel):
    """모든 응답을 감싸는 공통 형태."""

    code: str = Field(description="기계 판독 코드 (예: OK, NOT_FOUND)")
    message: str = Field(description="사람이 읽는 메시지")
    data: T | None = Field(default=None, description="실제 페이로드")


def success[T](data: T, message: str = "ok") -> ApiEnvelope[T]:
    return ApiEnvelope[T](code="OK", message=message, data=data)
