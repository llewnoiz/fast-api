"""Dead Letter Queue — 처리 실패 메시지 격리 + 재처리.

문제:
    consumer 가 메시지 처리 실패 시 _3가지 선택지_:
    1) 재시도 무한 — _독성 메시지_ (poison pill) 가 큐를 막음
    2) 그냥 ack — 메시지 _영원히 사라짐_
    3) DLQ 로 보냄 — 격리 + 분석 + 수동/자동 재처리

**DLQ 운영 패턴**:
    - 재시도 횟수 _임계_ (예: 5회) 초과 시 DLQ 로
    - DLQ 메시지에 _원인 메타데이터_ 동봉: `error`, `retries`, `original_topic`, `failed_at`
    - 알람 — DLQ 깊이가 임계 넘으면 oncall 호출
    - 재처리 도구: DLQ → _수동 또는 자동_ → original topic 재투입

**Kafka 에서 DLQ 구현 4가지**:

A. **별도 DLQ 토픽** — 가장 흔함. 원본 + suffix (`orders.dlq`, `orders-dlq`)
B. **Header 기반 라우팅** — Kafka Streams / Flink 처리 중 실패 시 메타 첨부 후 DLQ
C. **Schema Registry DLQ** — 스키마 위반 메시지 자동 격리
D. **Connect SinkConnector** errant.tolerance + DLQ topic 자동 처리

**Redis 기반 큐의 DLQ** (arq, RQ):
    - arq 는 `keep_result_forever=False` + 재시도 한도, 실패 시 _failed jobs_ 키에.
    - 본 모듈은 _최소 모형_: `pending` 큐 + `dlq` 큐 + 재시도 카운터.

**재처리 안티패턴**:
    - DLQ 자동 재처리 _무한 루프_ (스키마 영구 깨진 메시지) ── 재시도 _상한_ 필수.
    - DLQ 영원히 보관 ── 디스크 폭발. _N 일 후 archive_.
    - 재처리 시 _원본 순서_ 무시 ── 도메인에 따라 큰 문제 (이체 순서 등).

비교:
    AWS SQS — DLQ 가 _내장_, redrive policy 한 줄
    RabbitMQ — `x-dead-letter-exchange` 큐 인자
    Kafka Streams — DeserializationExceptionHandler / errors.tolerance=all + dlq topic
    Sidekiq (Ruby) — dead set + retry queue, 웹 UI 에서 재처리
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import orjson
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass
class DLQConfig:
    main_queue: str
    dlq_queue: str
    max_retries: int = 3


class DLQProcessor:
    """단순 큐 처리기 — Redis list 기반.

    `enqueue` → `LPUSH main` ;  `process_one` → `RPOP main` 후 handler 실행.
    실패 시 _retry 카운터_ 증가 후 다시 LPUSH. 임계 넘으면 LPUSH dlq.
    """

    def __init__(self, redis: Redis, config: DLQConfig) -> None:
        self.redis = redis
        self.cfg = config

    async def enqueue(self, message: dict[str, object]) -> None:
        await self.redis.lpush(  # type: ignore[misc]
            self.cfg.main_queue, orjson.dumps({"msg": message, "retries": 0})
        )

    async def process_one(
        self, handler: Callable[[dict[str, object]], Awaitable[None]]
    ) -> str:
        """한 개 메시지 처리. 반환: 'ok' / 'retried' / 'dead' / 'empty'."""
        raw = await self.redis.rpop(self.cfg.main_queue)  # type: ignore[misc]
        if raw is None:
            return "empty"

        envelope = orjson.loads(raw)
        try:
            await handler(envelope["msg"])
            return "ok"
        except Exception as exc:  # noqa: BLE001
            envelope["retries"] += 1
            envelope["last_error"] = repr(exc)
            if envelope["retries"] >= self.cfg.max_retries:
                logger.warning(
                    "send to DLQ after %s retries: %s", envelope["retries"], envelope
                )
                await self.redis.lpush(  # type: ignore[misc]
                    self.cfg.dlq_queue, orjson.dumps(envelope)
                )
                return "dead"
            await self.redis.lpush(  # type: ignore[misc]
                self.cfg.main_queue, orjson.dumps(envelope)
            )
            return "retried"

    async def redrive(self, batch: int = 100) -> int:
        """DLQ → main 재투입. 운영 도구의 minimal 버전.

        주의: _자동_ 재투입은 무한 루프 위험. 운영은 _수동 트리거_ 또는 _스케줄_ + 한도.
        """
        moved = 0
        for _ in range(batch):
            raw = await self.redis.rpop(self.cfg.dlq_queue)  # type: ignore[misc]
            if raw is None:
                break
            envelope = orjson.loads(raw)
            envelope["retries"] = 0  # 재처리 시 카운터 리셋 (정책적 결정)
            await self.redis.lpush(  # type: ignore[misc]
                self.cfg.main_queue, orjson.dumps(envelope)
            )
            moved += 1
        return moved
