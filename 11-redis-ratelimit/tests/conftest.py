"""11 단계 테스트 fixture — testcontainers Redis."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from cacheapp.cache import Cache
from cacheapp.main import create_app
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis


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
    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def cache(redis_client: Redis) -> Cache:
    return Cache(redis_client, prefix="test:", default_ttl=10)


@pytest_asyncio.fixture
async def app_client(redis_url: str) -> AsyncIterator[AsyncClient]:
    """FastAPI 앱 + 진짜 Redis."""
    app = create_app()

    # lifespan 의 Redis 를 _테스트 컨테이너 URL_ 로 교체.
    # 가장 단순한 방법: settings 를 override (lifespan 안에서 get_settings 사용).
    # 여기선 기본 동작 그대로 가되, env 변수로 URL 주입.
    import os  # noqa: PLC0415

    os.environ["APP_REDIS_URL"] = redis_url
    # get_settings 의 lru_cache 비우기
    from cacheapp.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()

    # 매 테스트 격리 — flushdb
    rc = Redis.from_url(redis_url, decode_responses=True)
    await rc.flushdb()
    await rc.aclose()

    # asgi-lifespan 으로 lifespan 명시 트리거 (httpx ASGITransport 가 안 함)
    async with LifespanManager(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
