"""FastAPI e2e — 통합 동작 검증.

Sentry / OTel 은 _초기화 안 망가지는지_ 정도만 (외부 호출 X).
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200


def test_request_id_echoed(client: TestClient) -> None:
    """미들웨어가 X-Request-ID 응답 헤더에 echo."""
    r = client.get("/healthz")
    assert "x-request-id" in r.headers


def test_request_id_preserved_when_provided(client: TestClient) -> None:
    """클라이언트가 X-Request-ID 보내면 _그 값_ 사용."""
    rid = "test-fixed-id-123"
    r = client.get("/healthz", headers={"x-request-id": rid})
    assert r.headers["x-request-id"] == rid


def test_work_endpoint_creates_span(client: TestClient) -> None:
    r = client.get("/work/100")
    assert r.status_code == 200
    body = r.json()
    assert body["sum"] == sum(range(100))


def test_boom_returns_500_and_increments_slo(client: TestClient) -> None:
    r = client.post("/boom")
    assert r.status_code == 500
    burn = client.get("/slo/burn").json()
    assert burn["errors"] >= 1


def test_slo_burn_endpoint_initial_state(client: TestClient) -> None:
    """첫 호출 — burn rate 가 _숫자_ 로 반환."""
    r = client.get("/slo/burn")
    assert r.status_code == 200
    body = r.json()
    assert "burn_rate" in body
    assert "remaining_budget" in body


def test_dashboard_endpoint_returns_grafana_json(client: TestClient) -> None:
    r = client.get("/admin/dashboard.json")
    assert r.status_code == 200
    body = r.json()
    assert "panels" in body
    assert len(body["panels"]) == 3


def test_alerts_endpoint_returns_prometheus_rules(client: TestClient) -> None:
    r = client.get("/admin/alerts.yaml")
    assert r.status_code == 200
    body = r.json()
    assert "groups" in body
    assert len(body["groups"][0]["rules"]) == 4
