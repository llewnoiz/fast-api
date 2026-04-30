"""RedisBroker 통합 — 다른 인스턴스 시뮬레이션.

시나리오: 같은 Redis 에 broker 두 개 (manager 두 개 시뮬). A 가 publish 하면 B 도 받음.
"""

from __future__ import annotations

import asyncio

import pytest
from realtime.manager import ConnectionManager
from realtime.pubsub import RedisBroker
from redis.asyncio import Redis

from tests.conftest import FakeWebSocket

pytestmark = pytest.mark.integration


async def _wait_for(predicate, timeout: float = 2.0, interval: float = 0.05) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return False


async def test_publish_propagates_to_other_instance(redis_client: Redis) -> None:
    """Instance A publish → Instance B 의 ConnectionManager broadcast."""
    mgr_a = ConnectionManager()
    mgr_b = ConnectionManager()
    broker_a = RedisBroker(redis_client, mgr_a)
    broker_b = RedisBroker(redis_client, mgr_b)
    await broker_a.start()
    await broker_b.start()

    try:
        ws_b = FakeWebSocket()
        await mgr_b.connect("r1", ws_b)  # type: ignore[arg-type]

        await broker_a.publish("r1", {"hello": "from-A"})

        ok = await _wait_for(lambda: len(ws_b.sent) == 1)
        assert ok, f"expected B to receive, got {ws_b.sent}"
        assert ws_b.sent == [{"hello": "from-A"}]
    finally:
        await broker_a.stop()
        await broker_b.stop()


async def test_publish_isolates_rooms(redis_client: Redis) -> None:
    mgr = ConnectionManager()
    broker = RedisBroker(redis_client, mgr)
    await broker.start()

    try:
        ws_a = FakeWebSocket()
        ws_b = FakeWebSocket()
        await mgr.connect("rA", ws_a)  # type: ignore[arg-type]
        await mgr.connect("rB", ws_b)  # type: ignore[arg-type]

        await broker.publish("rA", {"target": "A"})
        await _wait_for(lambda: len(ws_a.sent) == 1)
        assert ws_a.sent == [{"target": "A"}]
        assert ws_b.sent == []
    finally:
        await broker.stop()


async def test_publish_returns_subscriber_count(redis_client: Redis) -> None:
    """`PUBLISH` 명령은 _전달된 구독자 수_ 반환."""
    mgr = ConnectionManager()
    broker = RedisBroker(redis_client, mgr)
    await broker.start()
    try:
        # broker 자신이 PSUBSCRIBE 중이라 최소 1 구독자.
        receivers = await broker.publish("r1", {"x": 1})
        assert receivers >= 1
    finally:
        await broker.stop()
