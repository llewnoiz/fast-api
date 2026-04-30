"""Redis Pub/Sub Broker — _다중 인스턴스_ 브로드캐스트.

문제:
    인스턴스 A 의 사용자 1 이 메시지 보냄 → 인스턴스 B 에 연결된 사용자 2 가 받지 못함.
    `ConnectionManager` 는 한 프로세스만 알기 때문.

해결:
    - 모든 인스턴스가 _같은 Redis 채널_ 을 SUBSCRIBE
    - 메시지 보낼 때 PUBLISH 로 Redis 에 → 모든 인스턴스 받음 → 각자 자신의 WebSocket 으로 fan-out
    - WebSocket 종료 / 새 연결은 인스턴스 _로컬_ 만 관리

**Redis pub/sub 의 한계** (운영 시 알아두기):
    - **at-most-once** ── 구독 안 하던 시점 메시지 누락. _재전송 X_.
    - **persistence X** ── Redis 가 죽으면 메시지 사라짐.
    - **scale 한계** ── 채널 수 / 메시지 양에 따라 단일 Redis 부하.
    → 영속/순서/내구성 필요 → **Kafka** (13 단계). pub/sub 은 _가벼운 fan-out_ 전용.

**대안**:
    - **Redis Streams** (`XADD` / `XREAD`) — 영속 + consumer group.
    - NATS — 가벼운 메시징, JetStream 으로 영속.
    - Kafka — 운영급 표준.
    - Postgres LISTEN/NOTIFY (A6 단계) — DB 만으로 가벼운 신호.

본 모듈은 _학습 친화_ Redis pub/sub. 운영은 패턴 같고 broker 만 교체.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Any

import orjson
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from realtime.manager import ConnectionManager

logger = logging.getLogger(__name__)


class RedisBroker:
    """다중 인스턴스 fan-out — `publish(room, msg)` → 모든 인스턴스의 ConnectionManager 가 broadcast.

    사용:
        broker = RedisBroker(redis, manager, channel_prefix="rt:")
        await broker.start()                  # 백그라운드 listener 태스크 시작
        await broker.publish("room1", {...})  # 모든 인스턴스에 전파
        await broker.stop()                   # graceful shutdown

    Redis 채널 = `{channel_prefix}{room}`. 한 번에 _모든 room 패턴 구독_ (PSUBSCRIBE).
    """

    def __init__(
        self,
        redis: Redis,
        manager: ConnectionManager,
        *,
        channel_prefix: str = "rt:",
    ) -> None:
        self.redis = redis
        self.manager = manager
        self.prefix = channel_prefix
        self._task: asyncio.Task[None] | None = None
        self._pubsub: PubSub | None = None

    async def start(self) -> None:
        """PSUBSCRIBE 후 백그라운드 listener 시작."""
        self._pubsub = self.redis.pubsub()
        await self._pubsub.psubscribe(f"{self.prefix}*")
        self._task = asyncio.create_task(self._listen(), name="rt-broker-listen")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._pubsub is not None:
            await self._pubsub.punsubscribe()
            await self._pubsub.aclose()
            self._pubsub = None

    async def publish(self, room: str, message: Any) -> int:
        """이 인스턴스 _포함_ 모든 인스턴스의 같은 room 에 전파."""
        channel = f"{self.prefix}{room}"
        return int(await self.redis.publish(channel, orjson.dumps(message)))

    async def _listen(self) -> None:
        assert self._pubsub is not None
        async for raw in self._iter_messages(self._pubsub):
            channel = (
                raw["channel"].decode()
                if isinstance(raw["channel"], bytes)
                else raw["channel"]
            )
            room = channel.removeprefix(self.prefix)
            try:
                payload = orjson.loads(raw["data"])
            except orjson.JSONDecodeError:
                logger.warning("invalid json on channel %s", channel)
                continue
            await self.manager.broadcast(room, payload)

    @staticmethod
    async def _iter_messages(pubsub: PubSub) -> AsyncIterator[dict[str, Any]]:
        """`pubsub.listen()` 의 thin wrapper — type 정제 + pmessage 만 통과."""
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg is None:
                continue
            if msg["type"] in ("pmessage", "message"):
                yield msg
