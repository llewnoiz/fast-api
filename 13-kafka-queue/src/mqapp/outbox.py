"""Transactional Outbox 패턴.

문제:
    DB 변경 + Kafka 발행을 _둘 다_ 해야 하는데, 둘은 _다른 시스템_.
    한 쪽 성공 후 다른 쪽 실패하면 _데이터 불일치_:
        - DB 만 성공: 다른 서비스가 새 상태 모름
        - Kafka 만 성공: 누군가 _없는_ 데이터에 반응

해결 — Outbox 패턴:
    1. 같은 _DB 트랜잭션_ 안에 outbox 테이블 행 INSERT (이벤트 페이로드)
    2. 별도 _릴레이 워커_ 가 outbox 폴링 → Kafka 발행 → 성공 시 행 마킹/삭제
    3. 트랜잭션 일관성 보장: DB 성공하면 _이벤트도 결국_ 발행됨

비교:
    Debezium CDC:    DB log (WAL) 직접 읽음 — outbox 테이블 없이도 가능 (더 강력)
    Spring Modulith: Application Events + outbox 자동
    NestJS:          @nestjs/cqrs + 직접 작성

본 단계는 _학습용 미니 구현_ — 마킹 방식 (status 컬럼).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from mqapp.kafka_producer import KafkaPublisher


class OutboxBase(DeclarativeBase):
    pass


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class OutboxEvent(OutboxBase):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(100))
    payload: Mapped[str] = mapped_column(String)         # JSON 문자열
    status: Mapped[str] = mapped_column(String(16), default=OutboxStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================================
# 사용자 코드 — _DB 트랜잭션 안에서_ 호출
# ============================================================================
#
# async with session.begin():
#     await session.execute(insert(Order).values(...))
#     await record_event(session, topic="order.created", key=str(order.id), payload={"id": ...})
# ── 여기서 둘 다 같은 트랜잭션 → 원자적 성공/실패
# ============================================================================


async def record_event(
    session: AsyncSession,
    *,
    topic: str,
    key: str,
    payload_json: str,
) -> OutboxEvent:
    event = OutboxEvent(topic=topic, key=key, payload=payload_json)
    session.add(event)
    await session.flush()    # id 채우기 (커밋은 호출자가)
    return event


# ============================================================================
# 릴레이 워커 — 별도 _태스크/프로세스_ 가 폴링하며 Kafka 로 발행
# ============================================================================


async def relay_once(session: AsyncSession, publisher: KafkaPublisher, *, batch: int = 50) -> int:
    """한 번 폴링 — PENDING 이벤트들을 Kafka 로 발행 후 SENT 마킹.

    배포 패턴: arq 또는 cron 으로 주기적 실행. 또는 별도 long-running task.

    멱등성: Kafka producer 의 `enable_idempotence=True` + 같은 (topic, partition, key)
    조합이면 같은 메시지 중복 송신해도 _브로커가 중복 제거_.
    """
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.status == OutboxStatus.PENDING)
        .order_by(OutboxEvent.id)
        .limit(batch)
    )
    events = list((await session.execute(stmt)).scalars().all())

    sent = 0
    for ev in events:
        try:
            import json  # noqa: PLC0415

            await publisher.publish(ev.key, json.loads(ev.payload))
            ev.status = OutboxStatus.SENT
            ev.sent_at = datetime.now(UTC)
            sent += 1
        except Exception:  # noqa: BLE001 — 학습용
            ev.status = OutboxStatus.FAILED
            # 운영: 실패 카운터, 재시도 정책, dead-letter

    await session.commit()
    return sent
