"""Descriptor 테스트."""

from __future__ import annotations

import pytest
from typingdeep.t05_descriptors import Account, Report


def test_positive_validates_on_set() -> None:
    acc = Account(initial=100)
    assert acc.balance == 100
    acc.balance = 50
    assert acc.balance == 50

    with pytest.raises(ValueError, match="must be positive"):
        acc.balance = -1


def test_descriptor_per_instance() -> None:
    """다른 인스턴스끼리 _격리_ — 같은 descriptor 객체지만 _값은 인스턴스별_."""
    a = Account(initial=10)
    b = Account(initial=20)
    a.balance = 99
    assert a.balance == 99
    assert b.balance == 20


def test_lazy_property_caches() -> None:
    """첫 접근에 계산 → 인스턴스 dict 에 저장. 두 번째부턴 _instance dict_ 가 hit."""
    r = Report()
    first = r.expensive_total
    second = r.expensive_total
    assert first == second == sum(range(1000))
    # `r.__dict__` 에 캐시되었는지
    assert "expensive_total" in r.__dict__
