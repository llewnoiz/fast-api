"""Pydantic 검증 메시지 다국어화."""

from __future__ import annotations

import pytest
from i18napp.pydantic_messages import translate_validation_error
from pydantic import BaseModel, EmailStr, Field, ValidationError


class UserModel(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr


def test_translates_required_field() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UserModel.model_validate({})

    errors = translate_validation_error(exc_info.value, locale="en")
    fields = {e["field"] for e in errors}
    assert "name" in fields or "email" in fields


def test_translates_min_length_with_param() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UserModel.model_validate({"name": "a", "email": "alice@example.com"})

    errors = translate_validation_error(exc_info.value, locale="en")
    name_err = next(e for e in errors if e["field"] == "name")
    # `must be at least 2 characters` 같은 메시지에 _2_ 포함되어야
    assert "2" in name_err["message"]


def test_translates_korean() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UserModel.model_validate({})

    errors = translate_validation_error(exc_info.value, locale="ko")
    # 한국어 메시지에 `필수` 포함
    assert any("필수" in e["message"] for e in errors)


def test_returns_list_of_dicts() -> None:
    """반환 형식 — `[{"field", "type", "message"}, ...]`."""
    with pytest.raises(ValidationError) as exc_info:
        UserModel.model_validate({})

    errors = translate_validation_error(exc_info.value, locale="en")
    for err in errors:
        assert {"field", "type", "message"} <= err.keys()
