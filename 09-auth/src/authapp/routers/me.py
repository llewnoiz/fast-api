"""/me — 현재 로그인 사용자 정보."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from authapp.deps import get_current_user
from authapp.users import User, UserPublic

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserPublic, summary="현재 사용자")
async def read_me(current: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    """`Depends(get_current_user)` 가 _자동으로_ Authorization 헤더를 검증.
    실패 시 401 — 라우트 코드 도달조차 안 함.
    """
    return UserPublic(
        username=current.username,
        full_name=current.full_name,
        roles=current.roles,
    )
