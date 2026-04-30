"""SLO / SLI / Error Budget — _운영의 신뢰성 계약_.

용어:
    **SLI** (Service Level Indicator): _측정값_. 예: 성공률, p95 latency.
    **SLO** (Service Level Objective): _목표값_. 예: "99.9% 성공률 / 30일 윈도우".
    **SLA** (Service Level Agreement): 고객과의 _계약_. 보통 SLO 보다 _느슨_ (여유).
    **Error Budget**: SLO 위반 _허용량_. 99.9% 이면 _한 달 43.2분_.

운영 가치:
    - 개발 vs 운영 _긴장 해소_: 에러 예산 _남으면_ 신규 기능 배포, _없으면_ 안정화.
    - 알람 _노이즈 줄임_: SLO 의 _번 다운_ 비율로 알람 (slow burn vs fast burn).
    - 우선순위: SLI 가 _직접_ 사용자 경험 반영하는지 검증.

본 모듈:
    - `Slo` 데이터클래스 (목표 + 윈도우)
    - `compute_error_budget` — 윈도우 동안 _허용 에러 분 수_
    - `compute_burn_rate` — 현재 _소진 속도_

비교:
    Google SRE Workbook 의 burn rate alerting
    Datadog SLO management — UI 로 정의 + 자동 알람
    Sloth (오픈소스) — Prometheus 룰 자동 생성
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Slo:
    """SLO 정의 — _목표_ + _측정 윈도우_.

    예: `Slo(target=0.999, window_minutes=43200)`  ← 30일 99.9% (월 43.2분 다운 허용)
    """

    target: float  # 0..1 (예: 0.999)
    window_minutes: int  # 측정 윈도우 (분)

    def __post_init__(self) -> None:
        if not 0 < self.target <= 1:
            raise ValueError(f"target must be in (0, 1]: {self.target}")
        if self.window_minutes <= 0:
            raise ValueError(f"window must be positive: {self.window_minutes}")


def compute_error_budget(slo: Slo) -> float:
    """SLO 의 _허용 에러 시간_ (분).

    99.9% / 30일 (43200분) → 43.2 분 허용.
    """
    return slo.window_minutes * (1 - slo.target)


def compute_burn_rate(*, errors: int, total: int, slo: Slo) -> float:
    """**Burn rate** — SLO 가 1 이면 정상, > 1 이면 예산 _빨리 소진_.

    burn_rate = (현재 에러율) / (1 - SLO.target)

    예: SLO 99.9% (예산 0.1%), 현재 에러율 1% → burn = 10x → 30일 예산을 _3일_ 에 소진.

    구글 SRE 알람 가이드:
        burn > 14.4 (1시간 윈도우) → 즉각 page (2% 예산이 1시간에 소진)
        burn >  6   (6시간 윈도우) → ticket (10% 예산이 6시간에 소진)
    """
    if total <= 0:
        return 0.0
    error_rate = errors / total
    allowed = 1 - slo.target
    if allowed <= 0:
        return float("inf") if error_rate > 0 else 0.0
    return error_rate / allowed


def remaining_budget(*, errors: int, total: int, slo: Slo) -> float:
    """남은 _에러 예산 비율_ (0~1, 1=손도 안 댐, 0=다 씀, 음수=초과).

    예산 = total * (1 - target).
    소비 = errors.
    """
    if total <= 0:
        return 1.0
    budget_total = total * (1 - slo.target)
    if budget_total <= 0:
        return 0.0
    return 1 - errors / budget_total


def is_alerting(*, errors: int, total: int, slo: Slo, threshold: float = 14.4) -> bool:
    """알람 발동 여부 — burn rate 기준.

    임계값 14.4 = 1시간 윈도우에서 _2%_ 예산 소진 (구글 SRE 권장).
    """
    return compute_burn_rate(errors=errors, total=total, slo=slo) > threshold
