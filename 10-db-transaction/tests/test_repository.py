"""Repository / UoW 동작 검증."""

from __future__ import annotations

import pytest
from dbapp.uow import UnitOfWork

pytestmark = pytest.mark.integration


class TestUserRepository:
    async def test_add_and_get_by_id(self, uow: UnitOfWork) -> None:
        u = await uow.users.add(username="alice", full_name="Alice Kim")
        assert u.id is not None

        got = await uow.users.get(u.id)
        assert got is not None
        assert got.username == "alice"

    async def test_get_by_username(self, uow: UnitOfWork) -> None:
        await uow.users.add(username="bob", full_name="Bob")
        u = await uow.users.get_by_username("bob")
        assert u is not None
        assert u.full_name == "Bob"

    async def test_unique_username(
        self, sessionmaker, clean_tables: None  # type: ignore[no-untyped-def]
    ) -> None:
        """UNIQUE 위반은 _다른 UoW_ 에서 검증.

        같은 UoW 안에서 IntegrityError 후 다음 작업은 PendingRollbackError —
        업무 단위 분리가 정석.
        """
        from sqlalchemy.exc import IntegrityError  # noqa: PLC0415

        async with UnitOfWork(sessionmaker) as uow:
            await uow.users.add(username="dup", full_name="One")
        # UoW 1 commit 완료

        with pytest.raises(IntegrityError):
            async with UnitOfWork(sessionmaker) as uow:
                await uow.users.add(username="dup", full_name="Two")
                # flush 시점에 UNIQUE 위반 → UoW __aexit__ 가 rollback


class TestEagerLoading:
    async def test_list_with_orders_no_n_plus_one(self, uow: UnitOfWork) -> None:
        # 사용자 3명, 각 2개 주문
        for name in ["a", "b", "c"]:
            user = await uow.users.add(username=name, full_name=name.upper())
            await uow.orders.add(user_id=user.id, item="X", quantity=1)
            await uow.orders.add(user_id=user.id, item="Y", quantity=2)

        users = await uow.users.list_with_orders()
        assert len(users) == 3
        # selectinload 덕에 _이미_ 로드됨 — 추가 쿼리 X
        for u in users:
            assert len(u.orders) == 2
