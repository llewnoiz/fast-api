"""Users 라우터 — POST /users (signup)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.envelope import ApiEnvelope, success
from app.db.uow import UnitOfWork
from app.deps.auth import get_uow
from app.schemas.users import UserCreate, UserPublic
from app.services import users_service as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=ApiEnvelope[UserPublic],
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
async def signup(
    payload: UserCreate,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[UserPublic]:
    user = await user_service.signup(uow, payload)
    return success(UserPublic.model_validate(user), message="created")
