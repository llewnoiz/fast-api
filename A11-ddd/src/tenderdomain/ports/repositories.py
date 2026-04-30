"""Repository Ports — Protocol 로 _도메인이 어떤 인프라가 필요한지_ 선언.

핵심 원칙:
    - 도메인은 _구현_ 모름. _필요한 인터페이스_ 만 선언.
    - 어댑터 (InMemoryRepo / SQLAlchemyRepo) 가 _구현_.
    - 의존성 방향: **Adapter → Domain** (Adapter 가 Domain 의 Port 구현). 절대 반대 X.

비교:
    Java: interface (`UserRepository extends JpaRepository<User, Long>`)
    Spring Data JPA — Repository 인터페이스만 선언, 구현 자동 (CRUD).
    Go: interface — 구조적 typing 으로 자연스러움
    Python: Protocol (PEP 544) — 같은 효과
"""

from __future__ import annotations

from typing import Protocol

from tenderdomain.domain.order import Order
from tenderdomain.domain.value_objects import OrderId, UserId


class OrderRepository(Protocol):
    async def add(self, order: Order) -> None: ...
    async def get(self, order_id: OrderId) -> Order | None: ...
    async def list_by_user(self, user_id: UserId) -> list[Order]: ...
    async def save(self, order: Order) -> None: ...


class UserRepository(Protocol):
    async def exists(self, user_id: UserId) -> bool: ...
