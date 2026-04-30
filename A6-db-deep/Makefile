.PHONY: help migrate downgrade run test test-int lint typecheck all clean

help:
	@echo "A6 — DB 심화 (인덱스 / N+1 / jsonb / FTS / LISTEN-NOTIFY / zero-downtime)"
	@echo ""
	@echo "  make migrate       — alembic upgrade head (psycopg sync)"
	@echo "  make downgrade     — alembic downgrade -1"
	@echo "  make run           — uvicorn dbdeep.main:app --reload"
	@echo "  make test          — pytest (testcontainers Postgres)"
	@echo "  make test-int      — integration 만"
	@echo "  make lint          — ruff check"
	@echo "  make typecheck     — mypy"
	@echo "  make all           — lint + typecheck + test"
	@echo ""
	@echo "사전: 05-infra-compose 의 postgres profile 띄우기 — 'make -C ../05-infra-compose up'"

migrate:
	cd $(CURDIR) && uv run alembic upgrade head

downgrade:
	cd $(CURDIR) && uv run alembic downgrade -1

run:
	cd $(CURDIR) && uv run uvicorn dbdeep.main:app --reload --port 8006

test:
	cd $(CURDIR) && uv run pytest -q

test-int:
	cd $(CURDIR) && uv run pytest -q -m integration

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
