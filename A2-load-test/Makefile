.PHONY: demo-server load-sync-async load-tender load-tender-headless lint

# ---------- sync vs async 비교 ----------

# 미니 데모 서버 — sync/async 두 라우트
demo-server:
	uv run uvicorn loadtest.demo_server:app --host 127.0.0.1 --port 8000

# locust GUI 모드 — http://localhost:8089
load-sync-async:
	uv run locust -f src/loadtest/sync_async_compare.py --host http://localhost:8000

# headless 모드 — 30초 부하
load-sync-async-headless:
	uv run locust -f src/loadtest/sync_async_compare.py \
		--host http://localhost:8000 \
		--users 100 --spawn-rate 20 --run-time 30s --headless --print-stats


# ---------- 15 tender 골든 패스 ----------

load-tender:
	uv run locust -f src/loadtest/tender_scenario.py --host http://localhost:8000

load-tender-headless:
	uv run locust -f src/loadtest/tender_scenario.py \
		--host http://localhost:8000 \
		--users 50 --spawn-rate 10 --run-time 60s --headless --print-stats


# ---------- 검증 ----------

lint:
	uv run ruff check src
