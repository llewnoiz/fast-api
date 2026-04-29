"""Repository — User, Order, OutboxEvent."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.errors import OrderNotFoundError
from tender.models import Order, OutboxEvent, User


class UserRepo:
    def __init__(self, s: AsyncSession) -> None:
        self._s = s

    async def get_by_username(self, username: str) -> User | None:
        return (
            await self._s.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()

    async def add(self, *, username: str, password_hash: str, role: str = "user") -> User:
        u = User(username=username, password_hash=password_hash, role=role)
        self._s.add(u)
        await self._s.flush()
        return u


class OrderRepo:
    def __init__(self, s: AsyncSession) -> None:
        self._s = s

    async def add(self, *, user_id: int, sku: str, quantity: int) -> Order:
        o = Order(user_id=user_id, sku=sku, quantity=quantity)
        self._s.add(o)
        await self._s.flush()
        return o

    async def get(self, order_id: int) -> Order:
        o = await self._s.get(Order, order_id)
        if o is None:
            raise OrderNotFoundError(order_id)
        return o

    async def list_by_user(self, user_id: int) -> list[Order]:
        stmt = select(Order).where(Order.user_id == user_id).order_by(Order.id.desc())
        return list((await self._s.execute(stmt)).scalars().all())


class OutboxRepo:
    def __init__(self, s: AsyncSession) -> None:
        self._s = s

    async def record(self, *, topic: str, key: str, payload: dict) -> OutboxEvent:
        ev = OutboxEvent(topic=topic, key=key, payload=json.dumps(payload))
        self._s.add(ev)
        await self._s.flush()
        return ev
