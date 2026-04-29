"""unit 테스트 — _외부 의존성 없는_ 순수 도메인 로직.

가장 빠르고 결정적. 매 PR 에서 _수백 개_ 가 도는 것이 정상.
"""

from __future__ import annotations

import pytest
from testapp.repository import discounted_price


# ---------- 단순 케이스 ----------
class TestDiscountedPrice:
    def test_no_discount(self) -> None:
        assert discounted_price(1000, 0) == 1000

    def test_full_discount(self) -> None:
        assert discounted_price(1000, 100) == 0

    @pytest.mark.parametrize(
        ("original", "percent", "expected"),
        [
            (1000, 10, 900),
            (1000, 25, 750),
            (1000, 33, 670),       # 정수 나눗셈 — 1000 * 67 // 100 = 670
            (777, 10, 699),        # 1000 → 777 케이스
            (0, 50, 0),            # 0원 입력
        ],
        ids=["10pct", "25pct", "33pct-truncated", "777-base", "zero-input"],
    )
    def test_various(self, original: int, percent: int, expected: int) -> None:
        assert discounted_price(original, percent) == expected

    @pytest.mark.parametrize("bad_percent", [-1, 101, 200])
    def test_rejects_invalid_percent(self, bad_percent: int) -> None:
        with pytest.raises(ValueError, match="0..100"):
            discounted_price(1000, bad_percent)
