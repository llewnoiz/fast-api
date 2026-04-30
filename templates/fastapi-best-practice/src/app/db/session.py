"""AsyncEngine + sessionmaker 팩토리 — lifespan 에서 호출, 테스트가 같은 헬퍼 사용."""

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
    """`expire_on_commit=False` — commit 후에도 객체 속성 접근 가능 (응답 직렬화 친화)."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
