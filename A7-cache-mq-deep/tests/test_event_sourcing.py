"""Event Sourcing 단위 테스트."""

from __future__ import annotations

import pytest
from cachemqdeep import event_sourcing as es


def test_replay_produces_current_state() -> None:
    store = es.EventStore()
    es.open_account(store, "acc-1", opening_balance=100)
    es.deposit(store, "acc-1", 50)
    es.withdraw(store, "acc-1", 30)

    agg = es.BankAccount.replay(store.load("acc-1"))
    assert agg.balance == 120
    assert agg.is_open is True


def test_withdraw_rejects_overdraft() -> None:
    store = es.EventStore()
    es.open_account(store, "acc-2", opening_balance=10)
    with pytest.raises(ValueError, match="insufficient"):
        es.withdraw(store, "acc-2", 100)


def test_close_account_event() -> None:
    store = es.EventStore()
    es.open_account(store, "acc-3", opening_balance=0)
    es.close_account(store, "acc-3")

    agg = es.BankAccount.replay(store.load("acc-3"))
    assert agg.is_closed is True
    assert agg.is_open is False


def test_events_have_increasing_sequence() -> None:
    store = es.EventStore()
    e1 = es.open_account(store, "acc-4", 0)
    e2 = es.deposit(store, "acc-4", 10)
    e3 = es.deposit(store, "acc-4", 20)
    assert (e1.sequence, e2.sequence, e3.sequence) == (1, 2, 3)


def test_streams_are_isolated() -> None:
    """다른 스트림의 이벤트는 _서로 영향 없음_."""
    store = es.EventStore()
    es.open_account(store, "acc-A", 100)
    es.open_account(store, "acc-B", 200)
    es.deposit(store, "acc-A", 50)

    a = es.BankAccount.replay(store.load("acc-A"))
    b = es.BankAccount.replay(store.load("acc-B"))
    assert a.balance == 150
    assert b.balance == 200
