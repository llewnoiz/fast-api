"""Saga 패턴 — 분산 트랜잭션의 _보상 트랜잭션_ 모델.

문제:
    마이크로서비스 환경에서 "_여러 서비스에 걸친 일관성_" 이 필요하지만 _전역 분산 락_
    (2PC) 은 운영 부담 + 가용성 ↓. 대신 각 단계 _보상 액션_ 을 정의해 실패 시 되돌림.

예시 (주문 생성):
    1) 결제 차감       → 보상: 결제 환불
    2) 재고 차감       → 보상: 재고 복원
    3) 배송 예약       → 보상: 배송 취소
    4) 주문 확정       → (마지막 — 이후 실패 시 모든 단계 보상)

두 가지 구현:

A. **Orchestration** ── 중앙 _코디네이터_ 가 단계 호출.
    - 흐름이 _명시적_, 디버깅 쉬움
    - 코디네이터 단일 장애점 (HA 필요)
    - _본 모듈 구현_

B. **Choreography** ── 각 서비스가 _이벤트 구독_ 으로 자율 실행.
    - 결합도 ↓, 추가 단계 _자유롭게_ 끼움
    - 흐름 추적 어려움 — _분산 trace 필수_

**보상 액션 설계 규칙**:
- _idempotent_ ── 같은 보상 두 번 실행해도 결과 동일. 재시도 안전.
- _commutative_ ── 가능하면 보상 순서 무관. 어렵다면 _역순_ 실행이 표준.
- _can never fail forever_ ── 재시도 한도 도달 시 _수동 개입 큐_ 로.

비교:
    Java Axon Framework Saga — annotation 기반, Spring 친화
    .NET MassTransit Saga — state machine
    Temporal / Cadence — workflow 엔진. saga + 재시도 + 장기 실행 워크플로 표준.
    AWS Step Functions — 매니지드 orchestration, JSON 기반
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SagaStep:
    """한 단계 — _action_ 과 _compensation_ 한 쌍."""

    name: str
    action: Callable[[dict[str, object]], Awaitable[object]]
    compensation: Callable[[dict[str, object]], Awaitable[None]] | None = None


@dataclass
class SagaResult:
    completed_steps: list[str] = field(default_factory=list)
    compensated_steps: list[str] = field(default_factory=list)
    error: str | None = None
    context: dict[str, object] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.error is None


class Saga:
    """Orchestrator — `add_step()` 으로 정의 후 `execute(context)`.

    동작:
        - 각 step 의 action 을 순차 실행. 결과를 context 에 저장.
        - 어느 단계가 실패하면 _이미 성공한 단계들의 compensation_ 을 _역순_ 으로 호출.
        - compensation 자체가 실패하면 로그 + 다음 단계 보상 진행 (best-effort).

    학습용 단순 구현. 운영급은:
        - 각 단계 _영속화_ (DB) → 코디네이터 재시작에도 진행 상태 보존
        - 재시도 + 백오프 + DLQ
        - 분산 trace 와 통합
        - Temporal 같은 workflow 엔진이 이 모든 걸 _맡아줌_
    """

    def __init__(self) -> None:
        self.steps: list[SagaStep] = []

    def add_step(
        self,
        name: str,
        action: Callable[[dict[str, object]], Awaitable[object]],
        compensation: Callable[[dict[str, object]], Awaitable[None]] | None = None,
    ) -> Saga:
        self.steps.append(SagaStep(name=name, action=action, compensation=compensation))
        return self

    async def execute(self, context: dict[str, object] | None = None) -> SagaResult:
        ctx: dict[str, object] = context if context is not None else {}
        result = SagaResult(context=ctx)

        for step in self.steps:
            try:
                outcome = await step.action(ctx)
                ctx[f"{step.name}_result"] = outcome
                result.completed_steps.append(step.name)
            except Exception as exc:  # noqa: BLE001
                result.error = f"{step.name}: {exc!r}"
                await self._compensate(result)
                return result

        return result

    async def _compensate(self, result: SagaResult) -> None:
        for step in reversed(self.steps):
            if step.name not in result.completed_steps:
                continue
            if step.compensation is None:
                continue
            try:
                await step.compensation(result.context)
                result.compensated_steps.append(step.name)
            except Exception:
                logger.exception("compensation %s failed", step.name)
