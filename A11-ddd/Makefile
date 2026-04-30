.PHONY: help run test lint typecheck all clean

help:
	@echo "A11 — DDD / 헥사고날 (Ports & Adapters)"
	@echo ""
	@echo "  make run         — uvicorn ... --port 8011"
	@echo "  make test        — pytest"
	@echo "  make lint / typecheck / all"

run:
	cd $(CURDIR) && uv run uvicorn tenderdomain.adapters.api.main:app --reload --port 8011

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
