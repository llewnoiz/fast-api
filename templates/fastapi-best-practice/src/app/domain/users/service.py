"""User Application Service — 얇은 layer.

규칙:
    - UoW 시작 + 도메인 호출 + DTO 변환만
    - 비즈니스 _법칙_ 은 도메인 모델에 (Mid 단순화는 service 에 일부 허용)
"""

from __future__ import annotations

from app.core.errors import (
    AuthError,
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
)
from app.core.security import hash_password, verify_password
from app.db.models import User
from app.db.uow import UnitOfWork
from app.domain.users.schemas import UserCreate


async def signup(uow: UnitOfWork, payload: UserCreate) -> User:
    """이메일/username 중복 검사 + bcrypt 해시 + DB 저장."""
    async with uow:
        if await uow.users.get_by_email(payload.email):
            raise EmailAlreadyExistsError()
        if await uow.users.get_by_username(payload.username):
            raise UsernameAlreadyExistsError()
        return await uow.users.add(
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )


async def authenticate(uow: UnitOfWork, *, email: str, password: str) -> User:
    """이메일 + 비밀번호 검증 → User 반환. 실패 시 AuthError."""
    async with uow:
        user = await uow.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthError("invalid email or password")
        if not user.is_active:
            raise AuthError("account disabled")
        return user
