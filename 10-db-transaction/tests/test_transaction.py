"""트랜잭션 / savepoint / 롤백 검증.

핵심 학습:
    - UoW 정상 종료 → commit
    - UoW 안에서 예외 → rollback
    - savepoint (begin_nested) → 부분 롤백
"""

from __future__ import annotations

import pytest
from dbapp.uow import UnitOfWork
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


class TestTransaction:
    async def test_normal_commit(
        self, sessionmaker: async_sessionmaker[AsyncSession], clean_tables: None
    ) -> None:
        # UoW 1: 정상 종료 → commit
        async with UnitOfWork(sessionmaker) as uow:
            await uow.users.add(username="ok", full_name="OK")

        # UoW 2: 새 트랜잭션 — 위에서 커밋된 데이터 보임
        async with UnitOfWork(sessionmaker) as uow:
            u = await uow.users.get_by_username("ok")
            assert u is not None

    async def test_exception_rollback(
        self, sessionmaker: async_sessionmaker[AsyncSession], clean_tables: None
    ) -> None:
        with pytest.raises(RuntimeError, match="oops"):
            async with UnitOfWork(sessionmaker) as uow:
                await uow.users.add(username="rollback_me", full_name="X")
                raise RuntimeError("oops")

        # 다른 트랜잭션에서 조회 — 롤백되어 _없어야_ 함
        async with UnitOfWork(sessionmaker) as uow:
            assert await uow.users.get_by_username("rollback_me") is None

    async def test_savepoint_partial_rollback(
        self, sessionmaker: async_sessionmaker[AsyncSession], clean_tables: None
    ) -> None:
        """begin_nested = SAVEPOINT — 안쪽만 롤백, 바깥은 살림."""
        async with UnitOfWork(sessionmaker) as uow:
            await uow.users.add(username="alice", full_name="Alice")

            # savepoint — 실패해도 바깥 트랜잭션엔 영향 X
            try:
                async with uow.session.begin_nested():
                    await uow.users.add(username="alice", full_name="DUP")  # UNIQUE 위반
            except IntegrityError:
                pass  # 안쪽 savepoint 만 롤백

            # alice 는 살아있어야 함 (커밋되어야)
            await uow.users.add(username="bob", full_name="Bob")

        # 새 트랜잭션 — alice / bob 둘 다 있음
        async with UnitOfWork(sessionmaker) as uow:
            assert await uow.users.get_by_username("alice") is not None
            assert await uow.users.get_by_username("bob") is not None
