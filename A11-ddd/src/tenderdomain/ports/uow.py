"""Unit of Work Port — 트랜잭션 경계 + Repository 묶음.

핵심:
    - 한 use case = 한 UoW = 한 트랜잭션 = (보통) _하나의 Aggregate_ 변경
    - `__aenter__` / `__aexit__` 으로 자동 commit/rollback
    - 도메인 이벤트는 commit _후_ publish (commit 실패 시 _발행 X_)

10 단계의 UoW 와 같은 패턴, 여기선 **Protocol** 로 추상화.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol

from tenderdomain.ports.repositories import OrderRepository, UserRepository


class UnitOfWork(Protocol):
    """`async with uow: ...` 컨텍스트.

    명시적 `commit()` 안 부르고 `with` 블록 끝나면 자동 commit (예외 시 rollback).
    이벤트 publish 는 _commit 직후_ — UoW 구현체가 책임.
    """

    orders: OrderRepository
    users: UserRepository

    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
