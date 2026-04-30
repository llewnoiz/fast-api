"""SLO / SLI / Burn rate 단위 테스트."""

from __future__ import annotations

import pytest
from obsdeep.slo import (
    Slo,
    compute_burn_rate,
    compute_error_budget,
    is_alerting,
    remaining_budget,
)


def test_slo_validates_target_range() -> None:
    Slo(target=0.999, window_minutes=43200)
    with pytest.raises(ValueError):
        Slo(target=0, window_minutes=60)
    with pytest.raises(ValueError):
        Slo(target=1.5, window_minutes=60)
    with pytest.raises(ValueError):
        Slo(target=0.99, window_minutes=0)


def test_error_budget_99_9_percent_30days() -> None:
    """99.9% / 30일 → 43.2분 허용."""
    slo = Slo(target=0.999, window_minutes=30 * 24 * 60)  # 43200
    budget = compute_error_budget(slo)
    assert budget == pytest.approx(43.2)


def test_burn_rate_at_slo_target_is_one() -> None:
    """에러율 = 허용량 → burn rate = 1.0 (정확히 SLO 한계)."""
    slo = Slo(target=0.999, window_minutes=43200)
    # 1000 요청, 1 에러 → 0.1% 에러율 = 허용량 (1 - 0.999)
    rate = compute_burn_rate(errors=1, total=1000, slo=slo)
    assert rate == pytest.approx(1.0, rel=0.01)


def test_burn_rate_double_consumption() -> None:
    """0.2% 에러율 → burn rate ≈ 2x (예산 _두 배_ 빨리 소진)."""
    slo = Slo(target=0.999, window_minutes=43200)
    rate = compute_burn_rate(errors=2, total=1000, slo=slo)
    assert rate == pytest.approx(2.0, rel=0.01)


def test_burn_rate_zero_total() -> None:
    """요청 0 일 때 burn rate 0 — division by zero 회피."""
    slo = Slo(target=0.999, window_minutes=60)
    assert compute_burn_rate(errors=0, total=0, slo=slo) == 0.0


def test_remaining_budget_full_when_no_errors() -> None:
    slo = Slo(target=0.999, window_minutes=43200)
    assert remaining_budget(errors=0, total=1000, slo=slo) == pytest.approx(1.0)


def test_remaining_budget_negative_when_exceeded() -> None:
    """예산 초과 → 음수."""
    slo = Slo(target=0.999, window_minutes=43200)
    # 5 errors / 1000 = 0.5% (예산은 0.1%) → 5x 초과
    rem = remaining_budget(errors=5, total=1000, slo=slo)
    assert rem < 0


def test_alert_fires_above_threshold() -> None:
    """burn rate > 14.4 → 알람."""
    slo = Slo(target=0.999, window_minutes=43200)
    # 20 errors / 1000 = 2% 에러율, burn = 20x
    assert is_alerting(errors=20, total=1000, slo=slo) is True


def test_alert_quiet_below_threshold() -> None:
    slo = Slo(target=0.999, window_minutes=43200)
    # 10 errors / 1000 = 1% 에러율, burn = 10x (< 14.4)
    assert is_alerting(errors=10, total=1000, slo=slo) is False
