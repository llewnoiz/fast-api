"""Grafana dashboard JSON 생성 검증."""

from __future__ import annotations

from obsdeep.dashboards import red_dashboard, slo_dashboard


def test_red_dashboard_has_3_panels() -> None:
    """Rate / Errors / Duration 패널."""
    d = red_dashboard(service="tender")
    j = d.to_json()
    assert j["title"] == "tender — RED"
    assert len(j["panels"]) == 3
    titles = [p["title"] for p in j["panels"]]
    assert "Request Rate (RPS)" in titles
    assert "Error Rate (%)" in titles
    assert any("Latency" in t for t in titles)


def test_red_dashboard_uses_service_filter() -> None:
    """모든 PromQL 에 `service="X"` 필터 포함."""
    d = red_dashboard(service="tender")
    j = d.to_json()
    for panel in j["panels"]:
        for target in panel["targets"]:
            assert 'service="tender"' in target["expr"]


def test_red_dashboard_p95_in_query() -> None:
    d = red_dashboard(service="tender")
    j = d.to_json()
    latency_panel = next(p for p in j["panels"] if "Latency" in p["title"])
    expr = latency_panel["targets"][0]["expr"]
    assert "histogram_quantile(0.95" in expr


def test_slo_dashboard_panels() -> None:
    d = slo_dashboard(service="tender", slo_target=0.999)
    j = d.to_json()
    assert j["title"] == "tender — SLO"
    assert any("Burn Rate" in p["title"] for p in j["panels"])
    assert any("Budget" in p["title"] for p in j["panels"])


def test_dashboard_json_serializable() -> None:
    """JSON 직렬화 가능 — Grafana import 친화."""
    import json  # noqa: PLC0415

    d = red_dashboard(service="x")
    serialized = json.dumps(d.to_json())
    assert "panels" in serialized
