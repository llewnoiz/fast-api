"""User Service 단위 테스트 — UoW mock 으로 _DB 없이_.

빠른 단위 (sub-second) — 비즈니스 규칙 회귀 검출. integration 테스트보다 _100x_ 빠름.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.core.errors import (
    AuthError,
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
)
from app.core.security import hash_password
from app.schemas.users import UserCreate
from app.services import users_service as service


@dataclass
class FakeUser:
    """SQLAlchemy User 모델 대용 ── service 가 _읽고 쓰는 속성_ 만 가짐."""

    id: int
    email: str
    username: str
    hashed_password: str
    role: str = "user"
    is_active: bool = True


@dataclass
class FakeUserRepo:
    """_매우 단순_ in-memory repo. service 가 호출하는 메서드만 흉내."""

    users: dict[int, FakeUser] = field(default_factory=dict)
    _next_id: int = 1

    async def get_by_email(self, email: str) -> FakeUser | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def get_by_username(self, username: str) -> FakeUser | None:
        return next(
            (u for u in self.users.values() if u.username == username), None
        )

    async def add(
        self, *, email: str, username: str, hashed_password: str, role: str = "user"
    ) -> FakeUser:
        u = FakeUser(
            id=self._next_id,
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=role,
        )
        self.users[u.id] = u
        self._next_id += 1
        return u


class FakeUoW:
    """`async with uow:` 패턴만 흉내. 트랜잭션 / commit 은 no-op."""

    def __init__(self) -> None:
        self.users = FakeUserRepo()

    async def __aenter__(self) -> FakeUoW:
        return self

    async def __aexit__(self, *_args: Any) -> None:
        pass


# ── tests ──


async def test_signup_creates_user_with_hashed_password() -> None:
    uow = FakeUoW()
    payload = UserCreate(
        email="alice@example.com", username="alice", password="password123"
    )
    user = await service.signup(uow, payload)

    assert user.email == "alice@example.com"
    assert user.username == "alice"
    # 평문 저장 X
    assert user.hashed_password != "password123"
    assert len(user.hashed_password) > 20  # bcrypt hash 형태


async def test_signup_duplicate_email_raises() -> None:
    uow = FakeUoW()
    p1 = UserCreate(
        email="dup@example.com", username="user1", password="password123"
    )
    p2 = UserCreate(
        email="dup@example.com", username="user2", password="password123"
    )
    await service.signup(uow, p1)
    with pytest.raises(EmailAlreadyExistsError):
        await service.signup(uow, p2)


async def test_signup_duplicate_username_raises() -> None:
    uow = FakeUoW()
    p1 = UserCreate(email="a@x.com", username="dup", password="password123")
    p2 = UserCreate(email="b@x.com", username="dup", password="password123")
    await service.signup(uow, p1)
    with pytest.raises(UsernameAlreadyExistsError):
        await service.signup(uow, p2)


async def test_authenticate_correct_password() -> None:
    uow = FakeUoW()
    await service.signup(
        uow,
        UserCreate(
            email="alice@example.com", username="alice", password="password123"
        ),
    )
    user = await service.authenticate(
        uow, email="alice@example.com", password="password123"
    )
    assert user.username == "alice"


async def test_authenticate_wrong_password_raises() -> None:
    uow = FakeUoW()
    await service.signup(
        uow,
        UserCreate(
            email="alice@example.com", username="alice", password="password123"
        ),
    )
    with pytest.raises(AuthError):
        await service.authenticate(
            uow, email="alice@example.com", password="wrong"
        )


async def test_authenticate_unknown_email_raises() -> None:
    uow = FakeUoW()
    with pytest.raises(AuthError):
        await service.authenticate(
            uow, email="ghost@example.com", password="x"
        )


async def test_authenticate_inactive_user_raises() -> None:
    uow = FakeUoW()
    # 직접 inactive user 추가
    uow.users.users[1] = FakeUser(
        id=1,
        email="bob@example.com",
        username="bob",
        hashed_password=hash_password("password123"),
        is_active=False,
    )
    uow.users._next_id = 2
    with pytest.raises(AuthError, match="disabled"):
        await service.authenticate(
            uow, email="bob@example.com", password="password123"
        )
