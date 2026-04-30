"""ErrorCode + DomainError 베이스 + 도메인 예외.

규칙:
    - ErrorCode 값은 _불변_. 추가만 OK, 변경/삭제는 _깨짐 변경_ (클라이언트 SDK 호환).
    - 도메인 코드는 _자기 언어_ 로 실패. HTTP 상태 / SQL 예외 직접 raise X — 어댑터 (handlers.py) 가 매핑.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION = "VALIDATION_ERROR"
    INTERNAL = "INTERNAL_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"


class DomainError(Exception):  # noqa: N818
    """모든 도메인 예외의 베이스. handlers.py 가 잡아서 envelope 응답."""

    def __init__(self, *, code: ErrorCode | str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code if isinstance(code, str) else code.value
        self.message = message
        self.status = status


# ── 인증/인가 ────────────────────────────────────────────────────


class AuthError(DomainError):  # noqa: N818
    def __init__(self, message: str = "invalid credentials") -> None:
        super().__init__(code=ErrorCode.UNAUTHORIZED, message=message, status=401)


class ForbiddenError(DomainError):  # noqa: N818
    def __init__(self, message: str = "forbidden") -> None:
        super().__init__(code=ErrorCode.FORBIDDEN, message=message, status=403)


class NotFoundError(DomainError):  # noqa: N818
    """일반 베이스 — 도메인별 NotFoundError 가 이걸 상속해도 OK.

    `BaseRepo[T].get_or_404` 의 default `not_found_error` 클래스.
    """

    def __init__(self, message: str = "resource not found") -> None:
        super().__init__(code=ErrorCode.NOT_FOUND, message=message, status=404)


# ── User ────────────────────────────────────────────────────────


class UserNotFoundError(NotFoundError):  # noqa: N818
    def __init__(self, message: str = "user not found") -> None:
        super().__init__(message=message)


class EmailAlreadyExistsError(DomainError):  # noqa: N818
    def __init__(self, message: str = "email already exists") -> None:
        super().__init__(code=ErrorCode.CONFLICT, message=message, status=409)


class UsernameAlreadyExistsError(DomainError):  # noqa: N818
    def __init__(self, message: str = "username already exists") -> None:
        super().__init__(code=ErrorCode.CONFLICT, message=message, status=409)


# ── Item ────────────────────────────────────────────────────────


class ItemNotFoundError(NotFoundError):  # noqa: N818
    def __init__(self, message: str = "item not found") -> None:
        super().__init__(message=message)


class ItemAccessDeniedError(DomainError):  # noqa: N818
    def __init__(self, message: str = "you do not own this item") -> None:
        super().__init__(code=ErrorCode.FORBIDDEN, message=message, status=403)
