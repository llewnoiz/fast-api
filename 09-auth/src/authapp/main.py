"""09 — FastAPI 앱 조립. CORS 미들웨어 + 라우터 등록.

CORS 가 먼저 — _브라우저에서_ 다른 origin 의 SPA(React/Vue 등) 가 호출 가능하게.
서버사이드(서버↔서버) 호출엔 CORS 무관. 12 단계 (서버간 통신) 에서 다시 다룸.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from authapp.routers import admin, auth, me
from authapp.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="auth-app",
        version="0.1.0",
        description="09 — 인증/인가 (JWT + OAuth2 password flow + RBAC)",
        lifespan=lifespan,
    )

    # CORS — 운영에선 _구체 origin_ 만, allow_credentials=True 면 wildcard 금지
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(admin.router)
    app.include_router(admin.auditor_or_admin_router)

    return app


app = create_app()
