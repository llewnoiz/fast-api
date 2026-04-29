"""Prometheus /metrics 노출 검증."""

from __future__ import annotations

from httpx import AsyncClient


class TestMetrics:
    async def test_metrics_endpoint_serves_prometheus_format(self, app_client: AsyncClient) -> None:
        # 한 번 healthz 쳐서 메트릭이 한 라벨 이상 생성되게
        await app_client.get("/healthz")

        r = await app_client.get("/metrics")
        assert r.status_code == 200
        body = r.text
        # Prometheus exposition format — `# HELP`, `# TYPE` 라인 + 메트릭 이름
        assert "# HELP" in body
        assert "# TYPE" in body
        # 기본 메트릭 — http_requests_total 또는 http_request_duration_seconds
        assert ("http_requests_total" in body) or ("http_request_duration_seconds" in body)
