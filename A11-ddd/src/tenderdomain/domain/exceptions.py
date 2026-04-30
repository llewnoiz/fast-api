"""도메인 예외 — 인프라 / 프레임워크 _무관_.

규칙:
    - 도메인 코드는 _자기 언어_ 로 실패. HTTP 상태 코드 / SQL 예외 _절대 X_.
    - 어댑터 (FastAPI handler 등) 가 도메인 예외 → HTTP 4xx 매핑.

비교:
    Spring `RuntimeException` 계열 + `@ControllerAdvice` 매퍼
    NestJS Domain Exception + Exception filter
"""

from __future__ import annotations


class DomainError(Exception):
    """모든 도메인 에러의 베이스."""


class InvariantViolation(DomainError):  # noqa: N818
    """Aggregate 불변식 깨짐 — 음수 수량, 빈 SKU 같은 경우."""


class OrderNotFound(DomainError):  # noqa: N818
    pass


class UserNotFound(DomainError):  # noqa: N818
    pass


class IllegalStateTransition(DomainError):  # noqa: N818
    """이미 결제된 주문 다시 결제 같은 _상태 머신 위반_."""
