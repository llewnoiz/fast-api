"""Unit of Work — 트랜잭션 경계 패턴.

비교:
    Spring `@Transactional`:    메서드 단위 트랜잭션, 예외 시 자동 롤백
    NestJS QueryRunner:         transaction { ... } 블록
    Kotlin Exposed transaction { ... }

UoW 의 가치:
    - 라우트 / 서비스 코드가 _커밋/롤백 직접 안 함_
    - 한 _업무 단위_ 안의 여러 Repository 가 _같은 세션_ 공유 (트랜잭션 경계 일치)
    - 예외 자동 롤백, 정상 종료 시 자동 커밋 — 휴먼 에러 방지

사용:
    async with uow:
        user = await uow.users.add(...)
        order = await uow.orders.add(user_id=user.id, ...)
        # with 블록 끝 = 자동 commit (예외 시 rollback)
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dbapp.repository import OrderRepository, UserRepository


class UnitOfWork:
    users: UserRepository
    orders: OrderRepository

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> UnitOfWork:
        self._session = self._sessionmaker()
        await self._session.begin()           # 명시적 트랜잭션 시작
        self.users = UserRepository(self._session)
        self.orders = OrderRepository(self._session)
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

    @property
    def session(self) -> AsyncSession:
        assert self._session is not None, "UoW 컨텍스트 안에서만 사용"
        return self._session
