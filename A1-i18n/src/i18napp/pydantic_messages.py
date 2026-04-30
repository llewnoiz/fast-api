"""Pydantic 검증 메시지 _다국어_.

Pydantic v2 의 검증 에러:
    영문 메시지 _하드코딩_ (예: "Field required", "Input should be a valid email").
    locale 변경 X.

해결 패턴:
    1. `ValidationError` 잡아서 _직접 번역_ — type / loc / msg 정보로 매핑
    2. 클라이언트가 _번역 키_ 로 받고 자체 번역 (가장 깨끗)
    3. 미들웨어에서 _서버 측_ 번역 후 응답

본 모듈: 1번 — 서버에서 `pydantic_core.ValidationError` → 다국어 envelope.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from i18napp.catalog import gettext

# Pydantic error type → 우리 카탈로그 키 매핑
_TYPE_TO_KEY: dict[str, str] = {
    "missing": "validation.required",
    "value_error": "validation.required",
    "string_too_short": "validation.min_length",
    "value_error.email": "validation.email",
}


def translate_validation_error(
    err: ValidationError, *, locale: str | None = None
) -> list[dict[str, Any]]:
    """`ValidationError` → 번역된 에러 목록.

    각 에러: `{"field": "name", "message": "..."}`.
    """
    out: list[dict[str, Any]] = []
    for e in err.errors():
        field = ".".join(str(p) for p in e["loc"])
        err_type = e["type"]
        key = _TYPE_TO_KEY.get(err_type, "validation.required")

        # 컨텍스트 ── min_length 같은 경우 ctx 에서 추가 인자
        ctx = e.get("ctx") or {}
        params: dict[str, Any] = {"field": field}
        if "min_length" in ctx:
            params["min"] = ctx["min_length"]

        out.append(
            {
                "field": field,
                "type": err_type,
                "message": gettext(key, locale=locale, **params),
            }
        )
    return out
