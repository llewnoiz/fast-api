"""Users 라우터 — POST /users (signup), POST /auth/login, GET /me."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.core.envelope import ApiEnvelope, success
from app.core.security import create_token
from app.db.models import User
from app.db.uow import UnitOfWork
from app.deps.auth import get_current_user, get_uow
from app.domain.users import service
from app.domain.users.schemas import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserPublic,
)

users_router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(tags=["users"])


@users_router.post(
    "",
    response_model=ApiEnvelope[UserPublic],
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    payload: UserCreate,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[UserPublic]:
    user = await service.signup(uow, payload)
    return success(UserPublic.model_validate(user), message="created")


@auth_router.post("/login", response_model=ApiEnvelope[TokenResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[TokenResponse]:
    user = await service.authenticate(
        uow, email=payload.email, password=payload.password
    )
    token = create_token(
        subject=user.username, role=user.role, settings=request.app.state.settings
    )
    return success(TokenResponse(access_token=token))


@me_router.get("/me", response_model=ApiEnvelope[UserPublic])
async def me(
    current: Annotated[User, Depends(get_current_user)],
) -> ApiEnvelope[UserPublic]:
    return success(UserPublic.model_validate(current))
