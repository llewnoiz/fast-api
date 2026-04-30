.PHONY: help run migrate test test-unit test-integration lint typecheck all clean docker-build compose-up compose-down

help:
	@echo "FastAPI best-practice 템플릿"
	@echo ""
	@echo "  make run              — uvicorn (개발 reload)"
	@echo "  make migrate          — alembic upgrade head"
	@echo "  make test             — 전체 pytest"
	@echo "  make test-unit        — 단위 테스트만 (도커 불필요)"
	@echo "  make test-integration — 통합 테스트만 (testcontainers)"
	@echo "  make lint             — ruff check"
	@echo "  make typecheck        — mypy"
	@echo "  make all              — lint + typecheck + test"
	@echo ""
	@echo "  make compose-up       — docker compose db + cache 띄우기"
	@echo "  make compose-down     — 정리"
	@echo "  make docker-build     — 앱 이미지 빌드"

run:
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

migrate:
	uv run alembic upgrade head

test:
	uv run pytest -v

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v -m integration

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

compose-up:
	docker compose --profile db --profile cache up -d

compose-down:
	docker compose --profile db --profile cache down

docker-build:
	docker build -t app:dev .

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
