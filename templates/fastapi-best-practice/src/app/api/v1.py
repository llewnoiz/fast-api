"""API v1 — `/api/v1/*` 라우터 통합.

도메인별 라우터 (users / items) 를 합치는 _진입점_.
새 도메인 추가 시 여기에 `include_router` 추가.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.items import router as items_router
from app.routers.me import router as me_router
from app.routers.users import router as users_router

router = APIRouter(prefix="/api/v1")
router.include_router(users_router)
router.include_router(auth_router)
router.include_router(me_router)
router.include_router(items_router)
