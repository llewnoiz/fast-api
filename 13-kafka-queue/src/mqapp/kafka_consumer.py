"""aiokafka consumer — 별도 프로세스/태스크로 실행.

비교:
    Spring Kafka:    @KafkaListener
    NestJS:          @MessagePattern
    Node:            kafkajs eachMessage

규칙:
    - **컨슈머 그룹** — 같은 그룹의 여러 인스턴스가 _파티션 분담_ (스케일 아웃)
    - **수동 commit** 권장 — 메시지 _처리 성공 후_ commit 으로 _at-least-once_ 보장
    - auto-commit 은 _처리 실패해도 commit_ 됨 → 메시지 유실 위험
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer

log = structlog.get_logger()

Handler = Callable[[str, dict[str, Any]], Awaitable[None]]


async def consume_loop(
    bootstrap: str,
    topic: str,
    group: str,
    handler: Handler,
    *,
    max_messages: int | None = None,   # 테스트용 — 정해진 수만 처리하고 종료
) -> AsyncIterator[None]:
    """컨슈머 메인 루프. 보통 _별도 프로세스_ 로 실행 (수동 워커 또는 K8s Deployment).

    `max_messages` 가 _아닌_ 운영에선 무한 루프 + signal handler 로 graceful shutdown.
    """
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group,
        enable_auto_commit=False,            # 수동 commit
        auto_offset_reset="earliest",         # 새 그룹은 _제일 처음_ 부터
    )
    await consumer.start()
    processed = 0
    try:
        async for msg in consumer:
            key = (msg.key or b"").decode("utf-8")
            value = json.loads((msg.value or b"{}").decode("utf-8"))
            try:
                await handler(key, value)
                await consumer.commit()      # _처리 성공_ 후 commit
                log.info("kafka.consumed", topic=topic, key=key, offset=msg.offset)
            except Exception as e:           # noqa: BLE001 — 학습용
                # 운영: dead-letter topic 으로 보내거나 재시도 큐
                log.exception("kafka.handler.failed", error=repr(e))
                # commit 안 함 → 같은 메시지 _재처리_

            processed += 1
            if max_messages is not None and processed >= max_messages:
                break
            yield None
    finally:
        await consumer.stop()
