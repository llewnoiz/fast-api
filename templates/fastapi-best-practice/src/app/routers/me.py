"""Me 라우터 — GET /me (본인 프로필)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.envelope import ApiEnvelope, success
from app.db.models import User
from app.deps.auth import get_current_user
from app.schemas.users import UserPublic

router = APIRouter(tags=["users"])


@router.get(
    "/me", response_model=ApiEnvelope[UserPublic], summary="내 프로필"
)
async def me(
    current: Annotated[User, Depends(get_current_user)],
) -> ApiEnvelope[UserPublic]:
    return success(UserPublic.model_validate(current))
