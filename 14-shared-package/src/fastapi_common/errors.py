"""ErrorCode + DomainError — 07 단계에서 추출.

규칙: ErrorCode 값은 _불변_. 추가만 OK, 변경/삭제는 _깨짐 변경_.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    # 일반
    VALIDATION = "VALIDATION_ERROR"
    INTERNAL = "INTERNAL_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"


class DomainError(Exception):
    """라이브러리는 _베이스만_ 제공. 사용자가 도메인별 예외를 상속해서 정의."""

    def __init__(self, *, code: ErrorCode | str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code if isinstance(code, str) else code.value
        self.message = message
        self.status = status
