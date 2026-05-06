"""User Repository — BaseRepo[User] 상속 + 도메인 특화 쿼리만."""

from __future__ import annotations

from sqlalchemy import select

from app.core.errors import UserNotFoundError
from app.db.models import User
from app.db.repository_base import BaseRepo


class UserRepo(BaseRepo[User]):
    model = User
    not_found_error = UserNotFoundError

    async def get_by_email(self, email: str) -> User | None:
        return (
            await self._s.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        return (
            await self._s.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()
