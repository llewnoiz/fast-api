"""/auth/token — OAuth2 Password Flow 의 토큰 발급 엔드포인트.

OAuth2PasswordRequestForm:
    application/x-www-form-urlencoded 로 받음 — 표준 OAuth2 형식.
    필드: username, password (+ 선택: scope, grant_type, client_id)
    Swagger UI 의 "Authorize" 버튼이 이 형식으로 호출.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from authapp.security import create_access_token, verify_password
from authapp.users import get_user

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse, summary="로그인 → 액세스 토큰")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    user = get_user(form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        # 사용자 _존재 여부_ 노출 X — username/password 둘 다 같은 메시지
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다",
        )
    if user.disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="비활성 계정")

    token = create_access_token(subject=user.username, roles=user.roles)
    return TokenResponse(access_token=token)
