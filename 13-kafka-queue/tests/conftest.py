"""13 단계 테스트 fixture.

Kafka 통합 테스트는 _testcontainers Kafka_ 가 무거움 (수십 초 시작 + 메모리).
학습용으론:
    - outbox 패턴은 _DB만_ 사용 — Postgres testcontainers 만
    - Kafka 통신 자체는 _별도_ 통합 (선택)
    - arq 는 testcontainers Redis
    - BackgroundTasks 는 _인메모리_ 검증
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from mqapp.main import create_app


def _docker_available() -> bool:
    try:
        import docker  # noqa: PLC0415

        docker.from_env(timeout=2).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


DOCKER_OK = _docker_available()


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    if not DOCKER_OK:
        pytest.skip("도커 데몬 없음")

    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        yield f"postgresql+asyncpg://{pg.username}:{pg.password}@{host}:{port}/{pg.dbname}"


@pytest_asyncio.fixture
async def app_client() -> AsyncIterator[AsyncClient]:
    """FastAPI 앱 — Kafka/arq _없이도_ 부팅 (lifespan 안에서 try/except).

    BackgroundTasks 라우트 검증에 사용.
    """
    app = create_app()
    async with LifespanManager(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
