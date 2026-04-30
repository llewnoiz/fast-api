"""Notifier Port — 도메인 이벤트 _publish_ 추상.

운영급 어댑터:
    - LogNotifier (학습/dev)
    - KafkaNotifier (13 단계 outbox + Kafka)
    - EmailNotifier
    - SlackNotifier
"""

from __future__ import annotations

from typing import Protocol

from tenderdomain.domain.events import DomainEvent


class Notifier(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
