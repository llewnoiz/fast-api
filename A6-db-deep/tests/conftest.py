"""A6 테스트 fixture — testcontainers Postgres + Alembic.

10 단계 패턴 그대로. 차이:
    - jsonb / GIN / tsvector 사용하므로 _진짜 Postgres_ 필수 (sqlite 대체 불가)
    - 매 테스트마다 deep_users / deep_posts / deep_comments TRUNCATE
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# Apple Silicon 등에서 testcontainers ryuk 가 컨테이너 정리 못 하는 케이스 회피.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

from dbdeep.database import make_engine, make_sessionmaker  # noqa: E402
from dbdeep.main import create_app  # noqa: E402
from dbdeep.seed import seed_data  # noqa: E402


def _docker_available() -> bool:
    try:
        import docker  # noqa: PLC0415

        docker.from_env(timeout=2).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


DOCKER_OK = _docker_available()


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[tuple[str, str]]:
    if not DOCKER_OK:
        pytest.skip("도커 데몬 없음")

    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        user = pg.username
        pwd = pg.password
        db = pg.dbname

        async_url = f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"
        sync_url = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"

        alembic_cwd = Path(__file__).resolve().parent.parent
        env = {**os.environ, "ALEMBIC_DATABASE_URL": sync_url}
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=alembic_cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"alembic upgrade 실패: {result.stderr}\n{result.stdout}")

        yield async_url, sync_url


@pytest.fixture(scope="session")
def async_url(postgres_container: tuple[str, str]) -> str:
    return postgres_container[0]


@pytest.fixture(scope="session")
def sync_url(postgres_container: tuple[str, str]) -> str:
    """psycopg sync URL — LISTEN/NOTIFY 같은 sync 데모용."""
    return postgres_container[1]


@pytest_asyncio.fixture
async def engine(async_url: str) -> AsyncIterator[AsyncEngine]:
    eng = make_engine(async_url, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
def sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return make_sessionmaker(engine)


@pytest_asyncio.fixture
async def clean_tables(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncIterator[None]:
    async with sessionmaker() as s:
        await s.execute(
            text(
                "TRUNCATE deep_comments, deep_posts, deep_users RESTART IDENTITY CASCADE"
            )
        )
        await s.commit()
    yield


@pytest_asyncio.fixture
async def seeded_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_tables: None,  # noqa: ARG001
) -> AsyncIterator[AsyncSession]:
    """시드된 데이터를 가진 세션 — User 30 / Post 90 / Comment ~수백."""
    async with sessionmaker() as s:
        await seed_data(s, users=30, posts_per_user=3)
    async with sessionmaker() as s:
        yield s


@pytest_asyncio.fixture
async def session(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_tables: None,  # noqa: ARG001
) -> AsyncIterator[AsyncSession]:
    """빈 세션 — 격리 보장."""
    async with sessionmaker() as s:
        yield s


@pytest_asyncio.fixture
async def app_client(
    sessionmaker: async_sessionmaker[AsyncSession],
    engine: AsyncEngine,
    clean_tables: None,  # noqa: ARG001
) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
