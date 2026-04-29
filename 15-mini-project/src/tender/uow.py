"""Unit of Work — 10 단계 패턴 + tender 도메인 Repo 묶음."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tender.repository import OrderRepo, OutboxRepo, UserRepo


class UnitOfWork:
    users: UserRepo
    orders: OrderRepo
    outbox: OutboxRepo

    def __init__(self, sm: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sm
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> UnitOfWork:
        self._session = self._sm()
        await self._session.begin()
        self.users = UserRepo(self._session)
        self.orders = OrderRepo(self._session)
        self.outbox = OutboxRepo(self._session)
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
