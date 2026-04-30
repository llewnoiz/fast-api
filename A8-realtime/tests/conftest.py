"""A8 fixture — testcontainers Redis (broker 통합 테스트용).

순수 manager 테스트는 Redis 불필요. broker / e2e 만 도커 의존.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
import pytest_asyncio
from redis.asyncio import Redis

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


@dataclass(eq=False)  # eq=False → 기본 hash 유지 (set 에 넣을 수 있어야 함)
class FakeWebSocket:
    """ConnectionManager 가 호출하는 인터페이스만 흉내 — 여러 테스트가 공유."""

    sent: list[Any] = field(default_factory=list)
    accepted: bool = False
    raise_on_send: bool = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: Any) -> None:
        if self.raise_on_send:
            raise RuntimeError("disconnected")
        self.sent.append(data)


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
