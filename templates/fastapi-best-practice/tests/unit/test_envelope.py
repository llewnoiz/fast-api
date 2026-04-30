"""ApiEnvelope 직렬화 + DomainError 매핑 테스트."""

from __future__ import annotations

from app.core.envelope import ApiEnvelope, success
from app.core.errors import (
    AuthError,
    DomainError,
    EmailAlreadyExistsError,
    ErrorCode,
    ItemAccessDeniedError,
    ItemNotFoundError,
)


def test_success_helper() -> None:
    env = success({"id": 1, "name": "alice"})
    assert env.code == "OK"
    assert env.message == "ok"
    assert env.data == {"id": 1, "name": "alice"}


def test_success_custom_message() -> None:
    env = success({"x": 1}, message="created")
    assert env.message == "created"


def test_envelope_serializable() -> None:
    env = ApiEnvelope[dict](code="OK", message="ok", data={"x": 1})
    dumped = env.model_dump()
    assert dumped == {"code": "OK", "message": "ok", "data": {"x": 1}}


def test_envelope_data_optional() -> None:
    env = ApiEnvelope[None](code="NOT_FOUND", message="missing")
    assert env.data is None


def test_domain_error_attributes() -> None:
    e = DomainError(code=ErrorCode.NOT_FOUND, message="x", status=404)
    assert e.code == "NOT_FOUND"
    assert e.message == "x"
    assert e.status == 404
    assert isinstance(e, Exception)


def test_auth_error_defaults() -> None:
    e = AuthError()
    assert e.code == "UNAUTHORIZED"
    assert e.status == 401


def test_email_conflict_status() -> None:
    e = EmailAlreadyExistsError()
    assert e.status == 409
    assert e.code == "CONFLICT"


def test_item_errors() -> None:
    nf = ItemNotFoundError()
    fb = ItemAccessDeniedError()
    assert nf.status == 404
    assert fb.status == 403
    assert fb.code == "FORBIDDEN"


def test_error_code_values_stable() -> None:
    """규칙: ErrorCode 문자열 값은 _불변_ (클라이언트 SDK 호환)."""
    assert ErrorCode.UNAUTHORIZED.value == "UNAUTHORIZED"
    assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
    assert ErrorCode.CONFLICT.value == "CONFLICT"
    assert ErrorCode.VALIDATION.value == "VALIDATION_ERROR"
    assert ErrorCode.INTERNAL.value == "INTERNAL_ERROR"
