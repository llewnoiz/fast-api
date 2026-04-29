"""aiokafka producer — 앱 lifespan 동안 _하나_, 의존성 주입.

비교:
    Spring Kafka:    KafkaTemplate (싱글톤 빈)
    NestJS:          ClientKafka (DI)
    Node:            kafkajs Producer

규칙:
    - producer 는 _재사용_, 매 publish 마다 만들지 않음
    - 메시지 직렬화는 _스키마_ 기반 권장 (Avro/Protobuf), 학습용으론 JSON
    - 키(key) 가 같으면 _같은 파티션_ → 순서 보장 (예: order_id 기반)
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer

log = structlog.get_logger()


class KafkaPublisher:
    def __init__(self, producer: AIOKafkaProducer, topic: str) -> None:
        self._producer = producer
        self._topic = topic

    async def publish(self, key: str, value: dict[str, Any]) -> None:
        """key 로 파티션 결정, value 는 JSON 직렬화."""
        payload = json.dumps(value).encode("utf-8")
        await self._producer.send_and_wait(self._topic, key=key.encode("utf-8"), value=payload)
        log.info("kafka.published", topic=self._topic, key=key)


async def make_producer(bootstrap: str) -> AIOKafkaProducer:
    """앱 lifespan 안에서 한 번 호출. 종료 시 stop().

    `acks="all"` — 모든 ISR 확인 (가장 안전, 느림)
    `enable_idempotence` — 같은 메시지 중복 발행 방지 (배달 _exactly-once_ 의 일부)
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap,
        acks="all",
        enable_idempotence=True,
        compression_type="gzip",
    )
    await producer.start()
    return producer
