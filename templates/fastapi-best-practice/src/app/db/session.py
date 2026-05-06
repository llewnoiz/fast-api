"""AsyncEngine + sessionmaker 팩토리 — lifespan 에서 호출, 테스트가 같은 헬퍼 사용."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_recycle: int = 1800,
    pool_timeout: int = 30,
) -> AsyncEngine:
    """앱 lifespan 동안 _하나_ 만 만들고 재사용. dispose() 잊지 말 것.

    풀 튜닝 가이드:
        - `pool_size`: 보통 워커당 5~20. 운영 부하 측정으로 결정.
        - `max_overflow`: 일시적 spike 흡수. _영구 초과는 풀 size 늘리기_.
        - `pool_recycle`: 클라우드 DB (RDS / Cloud SQL) 의 idle timeout 보다 _작게_ (보통 1800s).
        - `pool_timeout`: 풀 고갈 시 대기. 너무 길면 _요청 누적_, 짧으면 _실패율_ ↑.
        - `pool_pre_ping=True`: 매 checkout 시 1 query 추가 — _연결 끊김_ 자동 감지.
    """
    return create_async_engine(
        database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_timeout=pool_timeout,
        pool_pre_ping=True,
    )


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """`expire_on_commit=False` — commit 후에도 객체 속성 접근 가능 (응답 직렬화 친화)."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
