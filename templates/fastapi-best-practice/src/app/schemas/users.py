"""User 도메인 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=100)


class UserPublic(BaseModel):
    """`from_attributes=True` ── ORM 객체에서 자동 변환 (`.model_validate(user)`)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    role: str
    is_active: bool
    created_at: datetime


class OwnerSummary(BaseModel):
    """가벼운 owner 정보 — Item 응답에 포함될 때 (전체 UserPublic 보단 _최소_)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    """access + refresh 페어. 클라이언트는 access 만 Authorization 헤더, refresh 는 _안전 보관_.

    프론트엔드 권장: refresh 는 _httpOnly + Secure cookie_ (XSS 차단). 본 API 는
    JSON body 반환 — 클라이언트 (모바일/SPA) 가 적절히 저장.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
