"""요청/응답 Pydantic 스키마 — v1 / v2 공존."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------- v1 (구식, deprecated) ----------
class OrderCreateV1(BaseModel):
    item: str = Field(min_length=1, max_length=50, examples=["Pencil"])
    quantity: int = Field(gt=0, le=1000)


class OrderOutV1(BaseModel):
    id: int
    item: str
    quantity: int


# ---------- v2 (현재) ----------
class OrderCreateV2(BaseModel):
    sku: str = Field(min_length=1, max_length=30, pattern=r"^[A-Z0-9-]+$", examples=["PEN-001"])
    quantity: int = Field(gt=0, le=1000)


class OrderOutV2(BaseModel):
    id: int
    sku: str
    quantity: int
    status: str
    created_at: datetime


# ---------- 인증 ----------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: int
    username: str
    role: str
