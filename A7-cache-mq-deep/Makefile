.PHONY: help run test lint typecheck all clean

help:
	@echo "A7 — 캐시·MQ 심화 (stampede / Saga / CQRS / Event Sourcing / Schema Registry / DLQ)"
	@echo ""
	@echo "  make run         — uvicorn cachemqdeep.main:app --reload --port 8007"
	@echo "  make test        — pytest"
	@echo "  make lint        — ruff check"
	@echo "  make typecheck   — mypy"
	@echo "  make all         — lint + typecheck + test"
	@echo ""
	@echo "사전: 05-infra-compose 의 cache profile — 'make -C ../05-infra-compose up-cache'"

run:
	cd $(CURDIR) && uv run uvicorn cachemqdeep.main:app --reload --port 8007

test:
	cd $(CURDIR) && uv run pytest -q

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
