"""Item 도메인 스키마.

Layered 구조 ── User schema cross-import 자유 (한 방향: items → users).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.users import OwnerSummary


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)


class ItemUpdate(BaseModel):
    """둘 다 옵셔널 — 부분 업데이트 (PATCH 의미). 본 템플릿은 PUT 으로도 사용."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)


class ItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ItemDetail(ItemPublic):
    """ItemPublic + owner 정보 포함 — `GET /items/{id}/detail` 같은 풍부 응답.

    cross-domain 사용 예. Layered 구조라 schema cross-import 자유.
    """

    owner: OwnerSummary
