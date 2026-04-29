"""의존성 — `Depends(get_current_user)`, `Depends(require_role(...))`.

이게 _인증/인가의 표면적_ 핵심. 라우트 함수는 `current: User = Depends(...)` 만으로
"이 라우트는 _인증된 사용자_ 가 필요하다" 또는 "_admin 역할_ 이 필요하다" 를 선언.

비교:
    Spring:    `@PreAuthorize("hasRole('ADMIN')")`, `Authentication` 매개변수
    NestJS:    `@UseGuards(AuthGuard) @Roles('admin')` + `@CurrentUser()` 데코레이터
"""

from __future__ import annotations

from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from authapp.security import decode_access_token
from authapp.users import User, get_user

# `tokenUrl` — Swagger UI 의 "Authorize" 버튼이 _이 경로_ 로 로그인 요청 보냄.
# 실제 토큰 발급 라우트와 _일치_ 시켜야 함 (/auth/token).
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="인증 실패",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
) -> User:
    """토큰 → 디코드 → 사용자 조회 → 활성화 검사."""
    try:
        payload = decode_access_token(token)
    except pyjwt.PyJWTError as e:
        raise CREDENTIALS_EXC from e

    username = payload.get("sub")
    if not isinstance(username, str):
        raise CREDENTIALS_EXC

    user = get_user(username)
    if user is None or user.disabled:
        raise CREDENTIALS_EXC
    return user


def require_role(*required: str):
    """RBAC 의존성 _팩토리_ — 한 라우트에 여러 역할 _OR_ 로 검사.

    예: `dependencies=[Depends(require_role("admin"))]`
        혹은 `current = Depends(require_role("admin", "auditor"))`

    Spring `@PreAuthorize("hasAnyRole('ADMIN','AUDITOR')")` 자리.
    """

    async def _check(current: Annotated[User, Depends(get_current_user)]) -> User:
        if not (set(required) & set(current.roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"역할 부족 — 필요: {list(required)}",
            )
        return current

    return _check
