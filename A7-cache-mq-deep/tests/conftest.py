"""A7 fixture — testcontainers Redis.

stampede / DLQ 테스트는 _진짜 Redis_ 필요. 나머지 (saga / cqrs / ES / schema) 는
순수 Python 이라 Redis 없이 unit 테스트.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


def _docker_available() -> bool:
    try:
        import docker  # noqa: PLC0415

        docker.from_env(timeout=2).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


DOCKER_OK = _docker_available()


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    if not DOCKER_OK:
        pytest.skip("도커 데몬 없음")

    from testcontainers.redis import RedisContainer  # noqa: PLC0415

    with RedisContainer("redis:7-alpine") as r:
        host = r.get_container_host_ip()
        port = r.get_exposed_port(6379)
        yield f"redis://{host}:{port}"


@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url, decode_responses=False)
    await client.flushdb()
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def app_client(redis_url: str) -> AsyncIterator[AsyncClient]:
    os.environ["A7_REDIS_URL"] = redis_url
    from cachemqdeep.main import create_app  # noqa: PLC0415
    from cachemqdeep.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()

    rc = Redis.from_url(redis_url, decode_responses=False)
    await rc.flushdb()
    await rc.aclose()

    app = create_app()
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac,
    ):
        yield ac
