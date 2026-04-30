"""Prometheus Alertmanager 규칙 빌더.

알람 라이프사이클:
    1. **Prometheus** 가 PromQL 표현식을 _주기적_ 평가
    2. 표현식이 `for` 동안 true 면 _alert firing_
    3. **Alertmanager** 로 전달 — 그룹화 / silence / 라우팅
    4. 라우팅 → PagerDuty / Slack / Email / OpsGenie

알람 _좋은_ 설계 (Google SRE):
    - **사용자 영향 기반** — CPU 80% 같은 _리소스_ 알람보다 _증상_ 알람
    - **actionable** — _뭘 해야 하는지_ runbook 링크 첨부
    - **noise 최소화** — flapping (반복 fire/resolve) 방지 — `for: 5m`

**Multi-window multi-burn-rate** (Google SRE):
    - 빠른 알람 (5분 윈도우) + 천천히 알람 (1시간 윈도우) _둘 다_ 트리거
    - 빠른 + 느린 _둘 다_ true 일 때만 fire → false positive ↓

본 모듈:
    - `AlertRule` 데이터클래스
    - `slo_burn_rate_alerts` — SRE 표준 4종 알람 (high-fast / high-slow / low-fast / low-slow)
    - `to_yaml_dict` — Prometheus rules.yaml 형식
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AlertRule:
    alert: str
    expr: str
    duration: str = "5m"  # `for: ...`
    severity: str = "warning"  # warning / critical
    summary: str = ""
    runbook_url: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        labels = {"severity": self.severity, **self.labels}
        annotations = {
            "summary": self.summary,
            **({"runbook_url": self.runbook_url} if self.runbook_url else {}),
            **self.annotations,
        }
        return {
            "alert": self.alert,
            "expr": self.expr,
            "for": self.duration,
            "labels": labels,
            "annotations": annotations,
        }


def slo_burn_rate_alerts(*, service: str, slo_target: float = 0.999) -> list[AlertRule]:
    """**구글 SRE Workbook** 표준 — multi-window multi-burn-rate.

    | 알람 | 빠른 윈도우 | 느린 윈도우 | burn rate | 의미 |
    |---|---|---|---|---|
    | page  | 5m  | 1h  | 14.4 | 1시간에 2% 예산 소진 |
    | page  | 30m | 6h  | 6    | 6시간에 5% 예산 소진 |
    | ticket| 2h  | 1d  | 3    | 1일에 10% 예산 소진 |
    | ticket| 6h  | 3d  | 1    | 3일에 10% 예산 소진 |

    빠른 + 느린 _둘 다_ true 여야 fire — false positive 줄임.
    """
    error_budget = 1 - slo_target

    def burn_expr(short: str, long: str, rate: float) -> str:
        """short / long 윈도우 burn rate _둘 다_ 검증하는 PromQL.

        f-string 안의 PromQL `{service="X"}` 는 _double brace_ 로 escape.
        """
        return (
            f'(sum(rate(slo_errors_total{{service="{service}"}}[{short}])) / '
            f'sum(rate(slo_total{{service="{service}"}}[{short}])) / {error_budget} > {rate})'
            f" and "
            f'(sum(rate(slo_errors_total{{service="{service}"}}[{long}])) / '
            f'sum(rate(slo_total{{service="{service}"}}[{long}])) / {error_budget} > {rate})'
        )

    return [
        AlertRule(
            alert=f"{service}_SLOFastBurn1h",
            expr=burn_expr("5m", "1h", 14.4),
            duration="2m",
            severity="critical",
            summary=f"{service} burning 2% error budget in 1h",
            runbook_url=f"https://runbooks.example.com/{service}/slo-burn",
        ),
        AlertRule(
            alert=f"{service}_SLOFastBurn6h",
            expr=burn_expr("30m", "6h", 6),
            duration="15m",
            severity="critical",
            summary=f"{service} burning 5% error budget in 6h",
            runbook_url=f"https://runbooks.example.com/{service}/slo-burn",
        ),
        AlertRule(
            alert=f"{service}_SLOSlowBurn1d",
            expr=burn_expr("2h", "1d", 3),
            duration="1h",
            severity="warning",
            summary=f"{service} burning 10% error budget in 1d",
            runbook_url=f"https://runbooks.example.com/{service}/slo-burn",
        ),
        AlertRule(
            alert=f"{service}_SLOSlowBurn3d",
            expr=burn_expr("6h", "3d", 1),
            duration="3h",
            severity="warning",
            summary=f"{service} budget projected to exhaust in 3d",
            runbook_url=f"https://runbooks.example.com/{service}/slo-burn",
        ),
    ]


def to_rules_yaml(group_name: str, rules: list[AlertRule]) -> dict[str, object]:
    """Prometheus `rules.yaml` 형식 dict (yaml 라이브러리는 별도)."""
    return {
        "groups": [
            {
                "name": group_name,
                "rules": [r.to_dict() for r in rules],
            }
        ]
    }
