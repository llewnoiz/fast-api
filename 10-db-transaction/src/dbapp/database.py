"""AsyncEngine + async_sessionmaker 팩토리.

비교:
    Spring:    DataSource + EntityManagerFactory (자동 구성)
    NestJS:    TypeOrmModule.forRoot(...) + DataSource
    Kotlin:    Database.connect(...) + transaction { } (Exposed)

핵심:
    - **Engine 은 _하나_**: 앱 lifespan 동안 재사용. _커넥션 풀_ 이 안에 있음.
    - **Session 은 _짧게_**: 요청 단위로 만들고 닫음. `Depends` 로 주입.
    - `async_sessionmaker(...)` 가 Session 을 _찍어내는 공장_.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """앱 lifespan 동안 _하나_ 만 만들고 재사용. dispose() 잊지 말 것."""
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """`expire_on_commit=False` — 커밋 후에도 객체 속성 접근 가능 (라우트 응답 직렬화 친화)."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
