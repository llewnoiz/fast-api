"""FastAPI 인증 의존성 — `get_current_user` + `require_role(*roles)`.

순수 함수 (`security.py`) 와 분리: 의존성 트리는 _FastAPI 전용_, 순수 함수는 _프레임워크 무관_.
"""

from __future__ import annotations

from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.errors import AuthError, ForbiddenError
from app.core.security import decode_token
from app.db.models import User
from app.db.uow import UnitOfWork
from app.domain.users.repository import UserRepo

# `tokenUrl` 은 _실제 라우트 prefix_ 와 일치해야 Swagger UI Authorize 동작
_oauth = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(_oauth)],
) -> User:
    """JWT → User. lifespan 에 등록된 sessionmaker / settings 사용."""
    settings = request.app.state.settings
    try:
        payload = decode_token(token, settings=settings)
    except pyjwt.PyJWTError as e:
        raise AuthError("invalid or expired token") from e

    username = payload.get("sub")
    if not isinstance(username, str):
        raise AuthError("malformed token")

    sm = request.app.state.sessionmaker
    async with sm() as session:
        repo = UserRepo(session)
        user = await repo.get_by_username(username)
    if user is None or not user.is_active:
        raise AuthError("user not found or disabled")
    return user


def require_role(*roles: str):
    """`Depends(require_role("admin"))` ── 역할 검증.

    빈 인자 (`require_role()`) 는 그냥 인증만 요구 — `get_current_user` 와 동일.
    """

    async def _check(current: Annotated[User, Depends(get_current_user)]) -> User:
        if roles and current.role not in roles:
            raise ForbiddenError(f"role required: {list(roles)}")
        return current

    return _check


def get_uow(request: Request) -> UnitOfWork:
    """라우트에서 `Depends(get_uow)` 로 새 UoW 인스턴스."""
    return UnitOfWork(request.app.state.sessionmaker)
