"""04/06 의 sync vs async 라우트 부하 비교 시나리오.

대상: 04 fastapi-hello 또는 _짧은 데모 앱_ 의 두 라우트 (예: /sync, /async).
06 의 인메모리 데모를 _진짜 부하 도구_ 로 재현.

실행:
    # 1) 데모 앱 띄우기 (별도 터미널)
    cd ../06-async-deep && uv run python -m asyncdeep.t07_fastapi_loadcompare
    # — 이건 _자체 데모_ 라 서버를 안 띄움. 대신 04 의 fastapi-hello 위에 추가하거나
    #   06 의 build_app 을 uvicorn 으로 띄워야 함.

    # 2) locust 실행
    cd A2-load-test
    uv run locust -f src/loadtest/sync_async_compare.py \
        --host http://localhost:8000 \
        --users 100 --spawn-rate 20 --run-time 30s --headless

비교:
    JMeter:  GUI 또는 jmx 파일 — 무거움
    Gatling: Scala DSL — 강력하지만 진입장벽
    k6:      JS 시나리오 — 가볍고 빠름, 클라우드 통합 좋음
    locust:  Python 시나리오 — 학습 친화, 분산 가능
    wrk:     C 도구 — 가장 빠름, 시나리오 작성은 Lua
"""

from __future__ import annotations

from locust import HttpUser, between, task


class SyncVsAsyncUser(HttpUser):
    """가상 사용자 1명의 행동 정의.

    `wait_time`: 두 task 사이 대기 (현실적 사용자 흉내).
    """

    wait_time = between(0.1, 0.3)

    @task(1)
    def call_sync(self) -> None:
        # name 인자: locust 통계에서 _묶음 표시_
        self.client.get("/sync", name="GET /sync")

    @task(1)
    def call_async(self) -> None:
        self.client.get("/async", name="GET /async")
