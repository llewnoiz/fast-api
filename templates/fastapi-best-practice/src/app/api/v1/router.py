"""API v1 router 통합 — feature 별 라우터를 `/api/v1` prefix 아래 묶음.

새 도메인 추가 시 이 파일에 `include_router(...)` 한 줄 추가.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.items import router as items_router
from app.api.v1.me import router as me_router
from app.api.v1.users import router as users_router

router = APIRouter(prefix="/api/v1")
router.include_router(users_router)
router.include_router(auth_router)
router.include_router(me_router)
router.include_router(items_router)
