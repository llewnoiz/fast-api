"""Domain Service — _Aggregate 에 자연히 속하지 않는_ 도메인 로직.

언제 사용?
    - _여러 Aggregate_ 협업이 필요한 비즈니스 규칙
    - 도메인 _법칙_ 인데 _Entity 의 책임_ 으로 두면 어색한 것 (예: 환율 변환)
    - 도메인 외부 자원이 _필요_ 하지만 _기술적 디테일은 추상화_ (Port)

규칙:
    - **stateless** (필요한 데이터는 인자로)
    - 인프라 의존 X (도메인 layer 안)
    - 외부 자원 필요시 _Port_ 인자로

비교:
    Spring `@Service` ── 광의로 — DDD 의 Domain Service 보다 더 큰 의미. 본 layer 와 구분.
    Axon `@CommandHandler` 메서드를 가진 클래스
"""

from __future__ import annotations

from dataclasses import dataclass

from tenderdomain.domain.value_objects import Money


@dataclass(frozen=True)
class DiscountPolicy:
    """학습용 단순 정책. 운영은 _프로모션 도메인_ 으로 분리되거나 별도 BC."""

    free_shipping_threshold: Money
    bulk_discount_min_items: int
    bulk_discount_percent: int

    def shipping_fee(self, total: Money) -> Money:
        if total.amount >= self.free_shipping_threshold.amount:
            return Money(0, total.currency)
        return Money(3000 if total.currency == "KRW" else 5, total.currency)

    def bulk_discount(self, total: Money, item_count: int) -> Money:
        """벌크 할인 _금액_ (양수) 반환. 적용 안 되면 0."""
        if item_count < self.bulk_discount_min_items:
            return Money(0, total.currency)
        discount = total.amount * self.bulk_discount_percent // 100
        return Money(discount, total.currency)
