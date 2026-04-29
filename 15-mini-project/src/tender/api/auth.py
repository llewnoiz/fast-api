"""/auth/token — 09 패턴."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from tender.auth import create_token, verify_password
from tender.errors import AuthError
from tender.schemas import TokenResponse
from tender.uow import UnitOfWork

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    sm = request.app.state.sessionmaker
    async with UnitOfWork(sm) as uow:
        user = await uow.users.get_by_username(form.username)
        if user is None or not verify_password(form.password, user.password_hash):
            raise AuthError("아이디 또는 비밀번호가 올바르지 않습니다")

        token = create_token(
            subject=user.username, role=user.role, settings=request.app.state.settings
        )
    return TokenResponse(access_token=token)
