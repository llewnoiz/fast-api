"""10 단계 테스트 fixture.

핵심:
    - testcontainers 로 진짜 Postgres
    - **Alembic 마이그레이션 자동 적용** (env 변수로 URL 주입)
    - 매 테스트마다 _깨끗한 상태_ — TRUNCATE
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from dbapp.database import make_engine, make_sessionmaker
from dbapp.main import create_app
from dbapp.uow import UnitOfWork
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# ============================================================================
# 도커 가용성
# ============================================================================


def _docker_available() -> bool:
    try:
        import docker  # noqa: PLC0415

        docker.from_env(timeout=2).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


DOCKER_OK = _docker_available()
# `pytestmark` 는 conftest 자체엔 효과 없음. 각 fixture 가 도커 없을 때 skip.


# ============================================================================
# session: Postgres 한 번 띄우고 _마이그레이션 적용_
# ============================================================================


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[tuple[str, str]]:
    """Postgres 컨테이너 + (async_url, sync_url) 튜플 반환.

    async_url: asyncpg — 앱이 사용
    sync_url:  psycopg — Alembic 이 사용
    """
    if not DOCKER_OK:
        pytest.skip("도커 데몬 없음")

    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        # 컨테이너의 host:port 추출 (driver=None 이라 표준 URL)
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        user = pg.username
        pwd = pg.password
        db = pg.dbname

        async_url = f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"
        sync_url = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"

        # Alembic 마이그레이션 적용 — 환경변수로 URL 주입
        alembic_cwd = Path(__file__).resolve().parent.parent
        env = {**os.environ, "ALEMBIC_DATABASE_URL": sync_url}
        result = subprocess.run(  # noqa: S603 — 학습용 신뢰 입력
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=alembic_cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"alembic upgrade 실패: {result.stderr}")

        yield async_url, sync_url


@pytest.fixture(scope="session")
def async_url(postgres_container: tuple[str, str]) -> str:
    return postgres_container[0]


# ============================================================================
# function: engine + sessionmaker (session-scope async 는 event loop 충돌 위험)
# 컨테이너만 session 으로 두고 engine 은 매 테스트마다 다시 — 빠른 편이라 비용 ↓.
# ============================================================================


@pytest_asyncio.fixture
async def engine(async_url: str) -> AsyncIterator[AsyncEngine]:
    eng = make_engine(async_url, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
def sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return make_sessionmaker(engine)


# ============================================================================
# function: 매 테스트마다 깨끗한 테이블
# ============================================================================


@pytest_asyncio.fixture
async def clean_tables(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncIterator[None]:
    """TRUNCATE — 격리. RESTART IDENTITY 로 시퀀스도 초기화."""
    async with sessionmaker() as s:
        await s.execute(__import__("sqlalchemy").text("TRUNCATE users RESTART IDENTITY CASCADE"))
        await s.commit()
    yield


@pytest_asyncio.fixture
async def uow(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_tables: None,  # noqa: ARG001 — autouse 트리거
) -> AsyncIterator[UnitOfWork]:
    async with UnitOfWork(sessionmaker) as u:
        yield u


# ============================================================================
# e2e: FastAPI 앱
# ============================================================================


@pytest_asyncio.fixture
async def app_client(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_tables: None,  # noqa: ARG001
) -> AsyncIterator[AsyncClient]:
    app = create_app()
    # lifespan 안에서 만드는 engine/sessionmaker 를 _테스트 컨테이너_ 로 교체
    app.state.sessionmaker = sessionmaker

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
