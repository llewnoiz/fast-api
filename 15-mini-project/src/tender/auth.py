"""인증 — 09 단순화 + tender.errors.AuthError 사용."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from tender.errors import AuthError
from tender.models import User
from tender.settings import Settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_token(*, subject: str, role: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_min)).timestamp()),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")


_oauth = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(_oauth)],
) -> User:
    """JWT → 사용자 조회. UoW 를 의존성으로 받음.

    학습용 _간단한_ 구현 — 09 의 RBAC 가드는 별도 require_role().
    """
    settings: Settings = request.app.state.settings
    try:
        payload = pyjwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except pyjwt.PyJWTError as e:
        raise AuthError() from e

    username = payload.get("sub")
    if not isinstance(username, str):
        raise AuthError()

    # UoW 통해 사용자 조회
    sm = request.app.state.sessionmaker
    from sqlalchemy import select  # noqa: PLC0415

    from tender.models import User as UserModel  # noqa: PLC0415

    async with sm() as session:
        result = await session.execute(select(UserModel).where(UserModel.username == username))
        user = result.scalar_one_or_none()
    if user is None:
        raise AuthError()
    return user


def require_role(*roles: str):
    async def _check(current: Annotated[User, Depends(get_current_user)]) -> User:
        if current.role not in roles:
            from fastapi_common import DomainError, ErrorCode  # noqa: PLC0415

            raise DomainError(
                code=ErrorCode.FORBIDDEN, message=f"role required: {roles}", status=403
            )
        return current

    return _check
