"""Auth 라우터 — login / refresh / logout / logout-all.

토큰 라이프사이클:
    1. POST /auth/login    → access + refresh 페어 발급, refresh jti Redis 저장
    2. POST /auth/refresh  → 옛 refresh 검증 → revoke (rotation) → 새 페어 발급
    3. POST /auth/logout   → 현재 refresh jti revoke (한 디바이스만)
    4. POST /auth/logout-all  → 사용자 모든 refresh revoke (전체 디바이스)
"""

from __future__ import annotations

from typing import Annotated

import jwt as pyjwt
from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis

from app.core.envelope import ApiEnvelope, success
from app.core.errors import AuthError
from app.core.refresh_store import (
    add_jti,
    is_valid,
    revoke,
    revoke_all_for,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.core.settings import Settings
from app.db.uow import UnitOfWork
from app.deps.auth import get_current_user, get_uow
from app.middleware.throttling import RateLimiter
from app.models import User
from app.schemas.users import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services import users_service as user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _refresh_ttl_seconds(settings: Settings) -> int:
    return settings.refresh_expire_days * 86400


async def _issue_token_pair(
    *, user: User, settings: Settings, redis: Redis
) -> TokenResponse:
    """access + refresh 페어 발급 + refresh jti Redis 저장."""
    access = create_access_token(
        subject=user.username, role=user.role, settings=settings
    )
    refresh, jti = create_refresh_token(subject=user.username, settings=settings)
    await add_jti(
        redis, jti=jti, subject=user.username, ttl_seconds=_refresh_ttl_seconds(settings)
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


# login brute-force 방지 — IP 당 분당 N회.
# `settings_attr` 패턴 → 환경변수 / 테스트 override 시 _runtime_ 반영.
_login_limiter = RateLimiter(
    key="login", settings_attr="rate_limit_login_per_min", seconds=60
)


@router.post(
    "/login",
    response_model=ApiEnvelope[TokenResponse],
    summary="로그인 — access + refresh 페어 발급 (rate limited)",
    dependencies=[Depends(_login_limiter)],
)
async def login(
    payload: LoginRequest,
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[TokenResponse]:
    user = await user_service.authenticate(
        uow, email=payload.email, password=payload.password
    )
    settings: Settings = request.app.state.settings
    redis: Redis = request.app.state.redis
    pair = await _issue_token_pair(user=user, settings=settings, redis=redis)
    return success(pair)


@router.post(
    "/refresh",
    response_model=ApiEnvelope[TokenResponse],
    summary="토큰 갱신 (rotation — 옛 refresh 자동 revoke)",
)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[TokenResponse]:
    """rotation: 옛 refresh 검증 → revoke → 새 access + refresh 발급."""
    settings: Settings = request.app.state.settings
    redis: Redis = request.app.state.redis

    try:
        decoded = decode_refresh_token(payload.refresh_token, settings=settings)
    except pyjwt.PyJWTError as e:
        raise AuthError("invalid or expired refresh token") from e

    subject = decoded.get("sub")
    jti = decoded.get("jti")
    if not isinstance(subject, str) or not isinstance(jti, str):
        raise AuthError("malformed refresh token")

    # Redis 화이트리스트 확인 — 이미 revoke 됐거나 다른 사용자 토큰이면 거부
    if not await is_valid(redis, jti=jti, subject=subject):
        raise AuthError("refresh token already used or revoked")

    # rotation: 옛 jti 즉시 revoke
    await revoke(redis, jti=jti)

    # 사용자 재조회 (비활성화됐을 수도)
    async with uow:
        user = await uow.users.get_by_username(subject)
    if user is None or not user.is_active:
        raise AuthError("user not found or disabled")

    pair = await _issue_token_pair(user=user, settings=settings, redis=redis)
    return success(pair)


@router.post(
    "/logout",
    response_model=ApiEnvelope[None],
    summary="현재 디바이스 로그아웃 (refresh 1개 revoke)",
)
async def logout(
    payload: RefreshRequest,
    request: Request,
) -> ApiEnvelope[None]:
    """현재 refresh 의 jti 만 revoke — 다른 디바이스 영향 X.

    클라이언트가 refresh 보내야 — access 만으론 jti 모름.
    """
    settings: Settings = request.app.state.settings
    redis: Redis = request.app.state.redis
    try:
        decoded = decode_refresh_token(payload.refresh_token, settings=settings)
        jti = decoded.get("jti")
        if isinstance(jti, str):
            await revoke(redis, jti=jti)
    except pyjwt.PyJWTError:
        # 이미 만료/위조 — 무시 (idempotent logout)
        pass
    return success(None, message="logged out")


@router.post(
    "/logout-all",
    response_model=ApiEnvelope[dict],
    summary="모든 디바이스 로그아웃 (사용자의 모든 refresh revoke)",
)
async def logout_all(
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
) -> ApiEnvelope[dict]:
    """access token 으로 인증 → 본인 모든 refresh 토큰 삭제."""
    redis: Redis = request.app.state.redis
    deleted = await revoke_all_for(redis, subject=current.username)
    return success({"revoked": deleted}, message="all sessions logged out")
