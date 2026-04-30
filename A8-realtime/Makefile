.PHONY: help run test lint typecheck all clean

help:
	@echo "A8 — WebSocket / Server-Sent Events / Redis pub/sub fan-out"
	@echo ""
	@echo "  make run         — uvicorn realtime.main:app --reload --port 8008"
	@echo "  make test        — pytest"
	@echo "  make lint        — ruff check"
	@echo "  make typecheck   — mypy"
	@echo "  make all         — lint + typecheck + test"

run:
	cd $(CURDIR) && uv run uvicorn realtime.main:app --reload --port 8008

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
