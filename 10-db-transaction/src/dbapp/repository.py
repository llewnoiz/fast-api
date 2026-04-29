"""Repository — _쿼리 메서드_ 모음. 트랜잭션 경계는 _상위_ (Service / UoW) 가 담당.

비교:
    Spring Data JPA:  `interface UserRepository : JpaRepository<User, Long>` (자동 구현)
    NestJS TypeORM:   `class UserRepository extends Repository<User>`
    Kotlin Exposed:   object UserRepo { fun byUsername(...) }

규칙:
    - Repository 는 _세션을 받음_, 새로 만들지 않음
    - **commit/rollback 은 Repository 가 _안 함_** — UoW / 라우트 핸들러 경계에서
    - N+1 회피: 관계 로드는 명시적 `selectinload` / `joinedload`
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dbapp.models import Order, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, *, username: str, full_name: str) -> User:
        user = User(username=username, full_name=full_name)
        self._session.add(user)
        await self._session.flush()      # id 채우기 (커밋은 X)
        return user

    async def get(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_with_orders(self) -> list[User]:
        """N+1 회피 — `selectinload` 로 orders 를 _별도 IN 쿼리_ 한 번에 로드.

        Spring `@OneToMany(fetch=FetchType.EAGER)` / `JOIN FETCH` 자리.
        """
        stmt = select(User).options(selectinload(User.orders)).order_by(User.id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_lazy(self) -> list[User]:
        """⚠ N+1 안티패턴 데모용 — orders 접근 시마다 쿼리 발생 (테스트에서 비교)."""
        stmt = select(User).order_by(User.id)
        return list((await self._session.execute(stmt)).scalars().all())


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, *, user_id: int, item: str, quantity: int) -> Order:
        order = Order(user_id=user_id, item=item, quantity=quantity)
        self._session.add(order)
        await self._session.flush()
        return order

    async def list_by_user(self, user_id: int) -> list[Order]:
        stmt = select(Order).where(Order.user_id == user_id).order_by(Order.id)
        return list((await self._session.execute(stmt)).scalars().all())
