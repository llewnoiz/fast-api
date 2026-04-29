"""08 — 테스트 공용 fixture.

핵심 학습: **fixture scope** + **testcontainers 자동 스킵** + **dependency_overrides**.

scope:
    function (기본) — 매 테스트마다 새로 만들고 정리. 가장 안전, 느림.
    module          — 같은 파일 안에서 공유.
    session         — 전체 테스트 세션 한 번. _도커 컨테이너_ 같이 비싼 자원에.

도커 데몬 안 켜져 있으면 testcontainers fixture 가 _자동 스킵_ → 통합 테스트 건너뜀.
"""

from __future__ import annotations

import socket
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection
from redis.asyncio import Redis
from testapp.main import (
    create_app,
)
from testapp.settings import Settings, get_settings

# ============================================================================
# 도커 가용성 검사 — testcontainers 통합 테스트 전체에 적용
# ============================================================================


def _docker_available() -> bool:
    """도커 데몬 소켓 살아있는지 빠르게 검사. testcontainers 가 띄우기 전에."""
    try:
        # docker.sock 또는 TCP. testcontainers 는 docker SDK 사용 → import 만으로 테스트 가능
        import docker  # noqa: PLC0415

        client = docker.from_env(timeout=2)
        client.ping()
        return True
    except Exception:  # noqa: BLE001 — 어떤 이유로든 도커 안 됨 = False
        return False


DOCKER_OK = _docker_available()
requires_docker = pytest.mark.skipif(not DOCKER_OK, reason="도커 데몬 안 켜져 있음 — 통합 테스트 스킵")


# ============================================================================
# session-scope: 비싼 컨테이너는 _전체 세션_ 동안 한 번만
# ============================================================================


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """testcontainers 로 진짜 Postgres 띄우고 URL 반환. 도커 없으면 _자동 스킵_."""
    if not DOCKER_OK:
        pytest.skip("도커 데몬 없음")

    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        # driver=None: psycopg 표준 URL (postgresql://...)
        url = pg.get_connection_url()
        yield url
    # with 블록 끝나면 컨테이너 자동 정리


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    if not DOCKER_OK:
        pytest.skip("도커 데몬 없음")

    from testcontainers.redis import RedisContainer  # noqa: PLC0415

    with RedisContainer("redis:7-alpine") as r:
        host = r.get_container_host_ip()
        port = r.get_exposed_port(6379)
        yield f"redis://{host}:{port}"


# ============================================================================
# function-scope: _매 테스트_ 마다 깨끗한 상태
# ============================================================================


@pytest_asyncio.fixture
async def db_conn(postgres_url: str) -> AsyncIterator[AsyncConnection]:
    conn = await AsyncConnection.connect(postgres_url)
    try:
        yield conn
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url, decode_responses=True)
    try:
        # 매 테스트 _시작 전_ 비우기 (격리)
        await client.flushdb()
        yield client
    finally:
        await client.aclose()


# ============================================================================
# e2e: FastAPI + 진짜 DB + 진짜 Redis
# dependency_overrides 로 _Settings_ 만 갈아끼움 — 가장 표준 패턴
# ============================================================================


@pytest_asyncio.fixture
async def app_client(postgres_url: str, redis_url: str) -> AsyncIterator[AsyncClient]:
    """진짜 컨테이너에 붙은 FastAPI 앱."""
    app = create_app()

    # Settings 만 _테스트 컨테이너 URL_ 로 교체. 다른 의존성은 Settings 를 통해 자동 흐름.
    def _test_settings() -> Settings:
        return Settings(database_url=postgres_url, redis_url=redis_url)

    app.dependency_overrides[get_settings] = _test_settings

    # 스키마 초기화
    async with await AsyncConnection.connect(postgres_url) as conn:
        from testapp.repository import ItemRepository  # noqa: PLC0415

        repo = ItemRepository(conn)
        await repo.init_schema()
        await repo.clear()

    # Redis 도 비우기
    redis = Redis.from_url(redis_url, decode_responses=True)
    await redis.flushdb()
    await redis.aclose()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ============================================================================
# 자유 포트 — 학습용 헬퍼 (필요 시)
# ============================================================================


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
