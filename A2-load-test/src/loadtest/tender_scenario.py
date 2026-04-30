"""15 tender 서비스 골든 패스 시나리오.

흐름:
    1. on_start: 사용자별로 _고유한_ username 생성 + DB 시드 (또는 _미리_ 시드)
    2. 로그인 → 토큰 받기
    3. v2/orders 생성 (가중치 3)
    4. v2/orders/{id} 조회 (가중치 5) — 캐시 hit rate 측정
    5. /healthz (가중치 1)

실행:
    # 1) tender 서버 + DB + Redis 띄우기 (다른 터미널)
    cd ../05-infra-compose && make up
    cd ../15-mini-project && make migrate && make run

    # 2) _미리_ 사용자 시드 (간단 INSERT 또는 endpoint 추가)
    #    학습용으론 conftest.register_user 패턴 응용 — 직접 SQL.

    # 3) locust 실행
    cd ../A2-load-test
    uv run locust -f src/loadtest/tender_scenario.py \
        --host http://localhost:8000 \
        --users 50 --spawn-rate 10 --run-time 60s --headless --print-stats

부하 형태 (학습 패턴):
    smoke   사용자 1~5, 1분 — 기본 동작 확인
    load    사용자 평소 트래픽 — 95th percentile latency 확인
    stress  사용자 점진 증가 — _한계점_ 발견
    spike   순간 폭증 — 자동 스케일링/회로 차단기 검증
    soak    낮은 부하 _긴 시간_ (수 시간) — 메모리 누수 / DB 풀 고갈
"""

from __future__ import annotations

import random

from locust import HttpUser, between, events, task

# 사용자 시드 — _미리_ DB 에 등록되어 있어야 함
SEED_USERS = [("alice", "alice123"), ("bob", "bob123"), ("carol", "carol123")]


class TenderUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self) -> None:
        """가상 사용자 시작 시 한 번 — 로그인."""
        username, password = random.choice(SEED_USERS)
        r = self.client.post(
            "/auth/token",
            data={"username": username, "password": password},
            name="POST /auth/token",
        )
        if r.status_code != 200:
            # 시드 사용자가 없으면 모든 task 실패할 것 — 정상 시나리오를 위해 알림
            print(f"⚠ 로그인 실패 — '{username}' 사용자 미시드: {r.status_code}")
            self.token = None
            return
        self.token = r.json()["access_token"]
        self.created_order_ids: list[int] = []

    @property
    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def create_order(self) -> None:
        if not self.token:
            return
        sku = random.choice(["PEN-001", "NOTE-001", "ERASER-001", "RULER-001"])
        r = self.client.post(
            "/v2/orders",
            json={"sku": sku, "quantity": random.randint(1, 5)},
            headers=self.auth_headers,
            name="POST /v2/orders",
        )
        if r.status_code == 201:
            self.created_order_ids.append(r.json()["data"]["id"])

    @task(5)
    def get_order(self) -> None:
        """이미 만든 주문 _하나_ 를 캐시 hit 노린다 — 첫 호출은 DB, 이후 캐시."""
        if not self.token or not self.created_order_ids:
            return
        order_id = random.choice(self.created_order_ids)
        self.client.get(
            f"/v2/orders/{order_id}",
            headers=self.auth_headers,
            name="GET /v2/orders/{id}",
        )

    @task(1)
    def healthz(self) -> None:
        self.client.get("/healthz", name="GET /healthz")


# ============================================================================
# 결과 요약 — 테스트 끝에 자동 출력
# ============================================================================


@events.test_stop.add_listener
def _on_test_stop(environment, **kwargs) -> None:  # type: ignore[no-untyped-def]  # noqa: ANN001, ARG001
    stats = environment.stats
    print("\n=== 부하 테스트 요약 ===")
    print(f"전체 요청 수: {stats.total.num_requests}")
    print(f"실패: {stats.total.num_failures}")
    print(f"평균 latency: {stats.total.avg_response_time:.0f}ms")
    print(f"p50 / p95 / p99: "
          f"{stats.total.get_response_time_percentile(0.5):.0f} / "
          f"{stats.total.get_response_time_percentile(0.95):.0f} / "
          f"{stats.total.get_response_time_percentile(0.99):.0f} ms")
    print(f"RPS: {stats.total.total_rps:.1f}")
