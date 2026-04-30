"""DLQ 처리 — Redis 통합 테스트."""

from __future__ import annotations

import pytest
from cachemqdeep.dlq import DLQConfig, DLQProcessor
from redis.asyncio import Redis

pytestmark = pytest.mark.integration


async def test_success_path(redis_client: Redis) -> None:
    dlq = DLQProcessor(redis_client, DLQConfig("q:main", "q:dlq"))
    await dlq.enqueue({"id": 1})

    async def handler(_msg: dict[str, object]) -> None:
        pass

    outcome = await dlq.process_one(handler)
    assert outcome == "ok"
    # 큐가 비었어야
    assert await redis_client.llen("q:main") == 0  # type: ignore[misc]


async def test_retry_then_dead(redis_client: Redis) -> None:
    cfg = DLQConfig("q:main", "q:dlq", max_retries=2)
    dlq = DLQProcessor(redis_client, cfg)
    await dlq.enqueue({"id": 7})

    async def handler(_msg: dict[str, object]) -> None:
        raise RuntimeError("boom")

    # 1차 실패 — retried
    o1 = await dlq.process_one(handler)
    assert o1 == "retried"
    # 2차 실패 — dead (retries == 2 reaches threshold)
    o2 = await dlq.process_one(handler)
    assert o2 == "dead"

    # main 비고, dlq 에 1 개
    assert await redis_client.llen("q:main") == 0  # type: ignore[misc]
    assert await redis_client.llen("q:dlq") == 1  # type: ignore[misc]


async def test_redrive_moves_back(redis_client: Redis) -> None:
    cfg = DLQConfig("q:main", "q:dlq", max_retries=1)
    dlq = DLQProcessor(redis_client, cfg)
    await dlq.enqueue({"id": 99})

    async def fail(_msg: dict[str, object]) -> None:
        raise RuntimeError("x")

    await dlq.process_one(fail)
    assert await redis_client.llen("q:dlq") == 1  # type: ignore[misc]

    moved = await dlq.redrive()
    assert moved == 1
    assert await redis_client.llen("q:dlq") == 0  # type: ignore[misc]
    assert await redis_client.llen("q:main") == 1  # type: ignore[misc]


async def test_empty_queue(redis_client: Redis) -> None:
    dlq = DLQProcessor(redis_client, DLQConfig("q:empty", "q:empty:dlq"))

    async def handler(_msg: dict[str, object]) -> None:
        pass

    assert await dlq.process_one(handler) == "empty"
