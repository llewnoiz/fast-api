"""공통 Pydantic 베이스 — ORM 객체에서 직접 변환하는 응답 스키마용.

`BaseSchema` 를 상속하면 `from_attributes=True` 가 기본 → `Schema.model_validate(orm_obj)` 가능.
입력 / 발급 스키마 (UserCreate / LoginRequest / TokenResponse 등) 는 `BaseModel` 그대로.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """ORM → 응답 스키마 공통 베이스. `from_attributes=True` 활성화."""

    model_config = ConfigDict(from_attributes=True)
