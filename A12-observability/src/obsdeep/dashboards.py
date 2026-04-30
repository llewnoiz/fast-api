"""Grafana Dashboard JSON 빌더.

Grafana 대시보드는 JSON 정의. UI 에서 만들 수도 있고 _코드로_ 정의해 git 에 commit 가능.

장점 (코드 정의):
    - 버전 관리 / 코드 리뷰
    - 환경별 (dev / staging / prod) 변형
    - 자동 배포 — `grafana-provisioning` / Terraform / API

운영 도구:
    - **grafonnet** (Jsonnet 기반) — Grafana 공식 추천
    - **grafanalib** (Python) — 본 모듈 패턴
    - **Terraform `grafana` provider** — IaC

본 모듈은 _최소_ JSON 빌더 — 학습용. 운영은 grafonnet / grafanalib.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Target:
    """Prometheus 쿼리 (PromQL). Grafana JSON 은 _camelCase_ 강제."""

    expr: str
    legendFormat: str = ""  # noqa: N815 — Grafana 스키마
    refId: str = "A"  # noqa: N815 — Grafana 스키마


@dataclass
class Panel:
    """Grafana 패널 — _하나의 차트_."""

    id: int
    title: str
    type: str  # "timeseries" / "stat" / "gauge" / "table"
    targets: list[Target]
    gridPos: dict[str, int] = field(  # noqa: N815 — Grafana 스키마
        default_factory=lambda: {"x": 0, "y": 0, "w": 12, "h": 8}
    )
    datasource: dict[str, str] = field(
        default_factory=lambda: {"type": "prometheus", "uid": "prometheus"}
    )


@dataclass
class Dashboard:
    title: str
    panels: list[Panel]
    schemaVersion: int = 39  # noqa: N815 — Grafana 스키마
    refresh: str = "30s"
    timezone: str = "browser"

    def to_json(self) -> dict[str, Any]:
        """Grafana import 가능한 _완전한_ dashboard JSON."""
        return {
            "title": self.title,
            "schemaVersion": self.schemaVersion,
            "refresh": self.refresh,
            "timezone": self.timezone,
            "panels": [asdict(p) for p in self.panels],
        }


def red_dashboard(*, service: str, prom_uid: str = "prometheus") -> Dashboard:
    """**RED 메서드** 대시보드 — Rate / Errors / Duration.

    공식 (Tom Wilkie, Weaveworks):
        - Rate: `sum(rate(http_requests_total{service="X"}[5m]))`
        - Errors: `sum(rate(http_requests_total{status=~"5..",service="X"}[5m]))`
        - Duration: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`
    """
    panels = [
        Panel(
            id=1,
            title="Request Rate (RPS)",
            type="timeseries",
            targets=[
                Target(
                    expr=f'sum(rate(http_requests_total{{service="{service}"}}[5m]))',
                    legendFormat="rps",
                )
            ],
            gridPos={"x": 0, "y": 0, "w": 8, "h": 8},
        ),
        Panel(
            id=2,
            title="Error Rate (%)",
            type="timeseries",
            targets=[
                Target(
                    expr=(
                        f'100 * sum(rate(http_requests_total{{service="{service}",status=~"5.."}}[5m])) / '
                        f'sum(rate(http_requests_total{{service="{service}"}}[5m]))'
                    ),
                    legendFormat="error %",
                )
            ],
            gridPos={"x": 8, "y": 0, "w": 8, "h": 8},
        ),
        Panel(
            id=3,
            title="p95 Latency (seconds)",
            type="timeseries",
            targets=[
                Target(
                    expr=(
                        "histogram_quantile(0.95, "
                        "sum(rate(http_request_duration_seconds_bucket"
                        f'{{service="{service}"}}[5m])) by (le))'
                    ),
                    legendFormat="p95",
                ),
                Target(
                    expr=(
                        "histogram_quantile(0.99, "
                        "sum(rate(http_request_duration_seconds_bucket"
                        f'{{service="{service}"}}[5m])) by (le))'
                    ),
                    legendFormat="p99",
                    refId="B",
                ),
            ],
            gridPos={"x": 16, "y": 0, "w": 8, "h": 8},
        ),
    ]
    # datasource uid 일관성
    for p in panels:
        p.datasource["uid"] = prom_uid
    return Dashboard(title=f"{service} — RED", panels=panels)


def slo_dashboard(*, service: str, slo_target: float = 0.999) -> Dashboard:
    """SLO 대시보드 — burn rate + 남은 예산.

    Prometheus 메트릭 가정:
        - `slo_errors_total{service="X"}`
        - `slo_total{service="X"}`
    """
    panels = [
        Panel(
            id=1,
            title=f"SLO Burn Rate (target {slo_target * 100}%)",
            type="timeseries",
            targets=[
                Target(
                    expr=(
                        f'sum(rate(slo_errors_total{{service="{service}"}}[1h])) / '
                        f'sum(rate(slo_total{{service="{service}"}}[1h])) / '
                        f'{1 - slo_target}'
                    ),
                    legendFormat="1h burn",
                )
            ],
            gridPos={"x": 0, "y": 0, "w": 12, "h": 8},
        ),
        Panel(
            id=2,
            title="Remaining Error Budget (%)",
            type="stat",
            targets=[
                Target(
                    expr=(
                        f'100 * (1 - sum(increase(slo_errors_total{{service="{service}"}}[30d])) / '
                        f'(sum(increase(slo_total{{service="{service}"}}[30d])) * {1 - slo_target}))'
                    ),
                    legendFormat="remaining",
                )
            ],
            gridPos={"x": 12, "y": 0, "w": 12, "h": 8},
        ),
    ]
    return Dashboard(title=f"{service} — SLO", panels=panels)
