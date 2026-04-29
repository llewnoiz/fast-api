"""Outbox 패턴 검증 — Postgres testcontainers + 가짜 Publisher.

핵심 검증: 같은 트랜잭션 안에서 INSERT 후 _롤백_ 되면 outbox 도 _없어야_ 한다.
"""

from __future__ import annotations

import json

import pytest
from mqapp.outbox import (
    OutboxBase,
    OutboxEvent,
    OutboxStatus,
    record_event,
    relay_once,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

pytestmark = pytest.mark.integration


class FakePublisher:
    """Kafka 흉내 — 호출 받은 (key, value) 만 기록."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    async def publish(self, key: str, value: dict) -> None:
        self.sent.append((key, value))


class TestOutboxAtomicity:
    async def test_record_then_rollback_leaves_no_event(self, postgres_url: str) -> None:
        """트랜잭션 _롤백_ 시 outbox 행도 사라져야 — 같은 DB 트랜잭션 안이라."""
        engine = create_async_engine(postgres_url)
        try:
            # drop + create — 매 테스트 격리
            async with engine.begin() as conn:
                await conn.run_sync(OutboxBase.metadata.drop_all)
                await conn.run_sync(OutboxBase.metadata.create_all)

            sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            # 트랜잭션 시작 → INSERT → 롤백
            async with sm() as session:
                await session.begin()
                await record_event(
                    session, topic="t", key="k", payload_json=json.dumps({"x": 1})
                )
                await session.rollback()

            # 다른 세션에서 조회 — 비어있어야
            async with sm() as session:
                from sqlalchemy import select  # noqa: PLC0415

                result = await session.execute(select(OutboxEvent))
                assert len(list(result.scalars().all())) == 0
        finally:
            await engine.dispose()

    async def test_record_then_commit_persists(self, postgres_url: str) -> None:
        engine = create_async_engine(postgres_url)
        try:
            # drop + create — 매 테스트 격리
            async with engine.begin() as conn:
                await conn.run_sync(OutboxBase.metadata.drop_all)
                await conn.run_sync(OutboxBase.metadata.create_all)

            sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            async with sm() as session:
                await session.begin()
                await record_event(
                    session, topic="t", key="k", payload_json=json.dumps({"x": 2})
                )
                await session.commit()

            async with sm() as session:
                from sqlalchemy import select  # noqa: PLC0415

                events = list(
                    (await session.execute(select(OutboxEvent))).scalars().all()
                )
                assert len(events) == 1
                assert events[0].status == OutboxStatus.PENDING
        finally:
            await engine.dispose()


class TestOutboxRelay:
    async def test_relay_publishes_pending_and_marks_sent(self, postgres_url: str) -> None:
        engine = create_async_engine(postgres_url)
        try:
            # drop + create — 매 테스트 격리
            async with engine.begin() as conn:
                await conn.run_sync(OutboxBase.metadata.drop_all)
                await conn.run_sync(OutboxBase.metadata.create_all)

            sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            # 3개 이벤트 기록
            async with sm() as session:
                await session.begin()
                for i in range(3):
                    await record_event(
                        session,
                        topic="orders.created",
                        key=str(i),
                        payload_json=json.dumps({"order_id": i}),
                    )
                await session.commit()

            # 릴레이 한 번
            publisher = FakePublisher()
            async with sm() as session:
                sent_count = await relay_once(session, publisher)  # type: ignore[arg-type]

            assert sent_count == 3
            assert len(publisher.sent) == 3
            assert publisher.sent[0] == ("0", {"order_id": 0})

            # 모두 SENT 로 마킹
            async with sm() as session:
                from sqlalchemy import select  # noqa: PLC0415

                events = list(
                    (await session.execute(select(OutboxEvent))).scalars().all()
                )
                assert all(e.status == OutboxStatus.SENT for e in events)
                assert all(e.sent_at is not None for e in events)
        finally:
            await engine.dispose()
