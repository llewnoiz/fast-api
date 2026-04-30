"""Unit of Work — 한 use case = 한 트랜잭션 = (보통) 하나의 Aggregate 변경.

`async with uow: ...` 자동 commit / rollback. 명시적 commit 호출 불필요.

확장 가이드:
    새 도메인 추가 시 이 클래스에 `repo` 필드 + `__aenter__` 에서 인스턴스화 추가.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.items.repository import ItemRepo
from app.domain.users.repository import UserRepo


class UnitOfWork:
    users: UserRepo
    items: ItemRepo

    def __init__(self, sm: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sm
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> UnitOfWork:
        self._session = self._sm()
        await self._session.begin()
        self.users = UserRepo(self._session)
        self.items = ItemRepo(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        if exc is None:
            await self._session.commit()
        else:
            await self._session.rollback()
        await self._session.close()
        self._session = None
