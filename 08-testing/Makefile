.PHONY: test test-unit test-integration test-e2e test-fast cov lint typecheck all run

# 기본: 전체 (도커 없으면 통합/e2e 자동 스킵)
test:
	uv run pytest tests/ -v

# 빠른 unit 만 (도커 무관)
test-unit:
	uv run pytest tests/ -v -m "not integration"

# 통합만 — 도커 데몬 필수
test-integration:
	uv run pytest tests/ -v -m "integration and not e2e"

# e2e 만
test-e2e:
	uv run pytest tests/ -v -m e2e

# 커버리지 — testapp 패키지에 한정
cov:
	uv run pytest tests/ --cov=src/testapp --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

# 학습용 — 진짜 서버 띄우기 (DB/Redis 가 _별도_ 로 돌고 있어야)
run:
	uv run uvicorn testapp.main:app --reload --host 127.0.0.1 --port 8000
