"""Prometheus 알림 규칙 빌더 테스트."""

from __future__ import annotations

from obsdeep.alerting import AlertRule, slo_burn_rate_alerts, to_rules_yaml


def test_alert_rule_to_dict_includes_severity_label() -> None:
    rule = AlertRule(
        alert="HighErrorRate",
        expr="error_rate > 0.05",
        severity="warning",
        summary="errors elevated",
    )
    d = rule.to_dict()
    assert d["alert"] == "HighErrorRate"
    assert d["labels"]["severity"] == "warning"  # type: ignore[index]
    assert d["annotations"]["summary"] == "errors elevated"  # type: ignore[index]


def test_slo_burn_rate_returns_4_alerts() -> None:
    """SRE Workbook 표준 — fast-page / slow-page / fast-ticket / slow-ticket."""
    rules = slo_burn_rate_alerts(service="tender", slo_target=0.999)
    assert len(rules) == 4
    names = [r.alert for r in rules]
    assert "tender_SLOFastBurn1h" in names
    assert "tender_SLOSlowBurn3d" in names


def test_slo_burn_alerts_have_runbooks() -> None:
    """모든 알람은 _runbook URL_ 포함 — actionable."""
    rules = slo_burn_rate_alerts(service="tender")
    for rule in rules:
        assert rule.runbook_url
        assert "runbook" in rule.runbook_url.lower()


def test_burn_rates_use_multi_window() -> None:
    """fast + slow 윈도우 _둘 다_ 검증 — false positive 줄임."""
    rules = slo_burn_rate_alerts(service="x")
    expr_first = rules[0].expr
    # 5m AND 1h 윈도우 모두 등장해야
    assert "[5m]" in expr_first
    assert "[1h]" in expr_first
    assert " and " in expr_first  # PromQL AND


def test_to_rules_yaml_structure() -> None:
    rules = slo_burn_rate_alerts(service="x")
    out = to_rules_yaml("x.slo", rules)
    assert out["groups"][0]["name"] == "x.slo"  # type: ignore[index]
    assert len(out["groups"][0]["rules"]) == 4  # type: ignore[index]
