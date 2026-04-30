"""Event Sourcing — 상태가 아니라 _이벤트 시퀀스_ 를 저장.

핵심 아이디어:
    `UPDATE accounts SET balance = 100` 대신 `INSERT INTO events (...) VALUES ('Deposited', 50)`.
    현재 상태는 _이벤트들의 누적_ (replay).

**장점**:
    - **완전한 audit log** ── 누가 언제 무엇을 왜 했는지 _자연스럽게_ 보존
    - **시간 여행** ── 임의 시점 상태 재구성 가능 (`SELECT * FROM events WHERE ts <= '2026-01-01'`)
    - **새 read model** ── 과거 이벤트 _리플레이_ 로 즉시 생성 (CQRS 와 자연 결합)
    - **debugging** ── "어떻게 이 상태가 됐지?" 가 _이벤트 로그 보면 끝_

**단점 / 함정**:
    - 학습 곡선 큼. 팀 _전체_ 가 모델 이해 필요.
    - 이벤트 _스키마 진화_ 가 어려움 (다음 모듈 schema_registry 참고).
    - 매번 replay 는 비싸 → **스냅샷** 으로 `state_at_event_N + events[N..]`.
    - "삭제" 가 어렵다 — `Deleted` 이벤트 추가지 _진짜 삭제_ 가 아님 (GDPR 충돌 가능).

**언제 쓸지**:
    - audit / 규정 (금융, 의료) — 자연스러움
    - 도메인이 _변화 자체_ 가 도메인 (주식, 게임 액션, 회계)
    - 읽기 모델 _여러 종류_ 필요 (검색, 분석, 대시보드 등)

**언제 쓰지 말지**:
    - 단순 CRUD — _복잡도 손해_.
    - 팀 첫 ES 프로젝트 + 빠듯한 일정.

본 모듈:
    - `Event` (불변 / 타임스탬프 / 타입)
    - `EventStore` (append + load by stream)
    - `Aggregate.replay(events)` ── 현재 상태 재구성
    - 예시: `BankAccount` ── Opened / Deposited / Withdrew / Closed

비교:
    EventStoreDB ── 전용 ES DB
    Apache Kafka + ksqlDB ── log-as-source-of-truth
    Axon Server (Java)
    Marten (.NET, Postgres jsonb 위)
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    """불변 이벤트. _과거에 일어난 일_ 이라 절대 안 바뀜."""

    stream_id: str
    type: str
    payload: dict[str, Any]
    sequence: int
    occurred_at: datetime


@dataclass
class EventStore:
    """학습용 인메모리 store. 운영은 Postgres jsonb / EventStoreDB / Kafka.

    스트림 = aggregate 인스턴스 ID (예: account-123). 같은 스트림 내 이벤트는 _순서 보장_.
    """

    _events: list[Event] = field(default_factory=list)
    _seq: dict[str, int] = field(default_factory=dict)

    def append(self, stream_id: str, event_type: str, payload: dict[str, Any]) -> Event:
        seq = self._seq.get(stream_id, 0) + 1
        self._seq[stream_id] = seq
        evt = Event(
            stream_id=stream_id,
            type=event_type,
            payload=payload,
            sequence=seq,
            occurred_at=datetime.now(UTC),
        )
        self._events.append(evt)
        return evt

    def load(self, stream_id: str) -> list[Event]:
        return [e for e in self._events if e.stream_id == stream_id]

    def all(self) -> list[Event]:
        return list(self._events)


# ─────────────────────────────────────────────────────────────────
# Aggregate ── _이벤트 시퀀스_ 로부터 _현재 상태_ 재구성
# ─────────────────────────────────────────────────────────────────


@dataclass
class BankAccount:
    """예시 aggregate. 메서드 = command, _내부적으로_ 이벤트 발생.

    실세계는 Aggregate 가 store 와 _분리_, command handler 가 store.append + apply.
    학습용으론 메서드에서 직접 store.append.
    """

    id: str
    balance: int = 0
    is_open: bool = False
    is_closed: bool = False

    @classmethod
    def replay(cls, events: Iterable[Event]) -> BankAccount:
        """과거 이벤트 _전부_ 로부터 현재 상태 재구성. ES 의 핵심."""
        events = list(events)
        if not events:
            raise ValueError("empty stream")
        agg = cls(id=events[0].stream_id)
        for e in events:
            agg._apply(e)
        return agg

    def _apply(self, e: Event) -> None:
        match e.type:
            case "AccountOpened":
                self.is_open = True
                self.balance = int(e.payload.get("opening_balance", 0))
            case "Deposited":
                self.balance += int(e.payload["amount"])
            case "Withdrew":
                self.balance -= int(e.payload["amount"])
            case "AccountClosed":
                self.is_open = False
                self.is_closed = True


def open_account(store: EventStore, account_id: str, opening_balance: int = 0) -> Event:
    return store.append(
        account_id, "AccountOpened", {"opening_balance": opening_balance}
    )


def deposit(store: EventStore, account_id: str, amount: int) -> Event:
    if amount <= 0:
        raise ValueError("amount must be positive")
    return store.append(account_id, "Deposited", {"amount": amount})


def withdraw(store: EventStore, account_id: str, amount: int) -> Event:
    if amount <= 0:
        raise ValueError("amount must be positive")
    # _현재 상태_ 를 replay 로 확인 — overdraft 방지
    current = BankAccount.replay(store.load(account_id))
    if current.balance < amount:
        raise ValueError("insufficient funds")
    return store.append(account_id, "Withdrew", {"amount": amount})


def close_account(store: EventStore, account_id: str) -> Event:
    return store.append(account_id, "AccountClosed", {})
