.PHONY: help run test lint typecheck all clean

help:
	@echo "A10 — GraphQL (Strawberry — Query / Mutation / DataLoader)"
	@echo ""
	@echo "  make run         — uvicorn gqlapi.main:app --reload --port 8010"
	@echo "  make test        — pytest"
	@echo "  make lint        — ruff check"
	@echo "  make typecheck   — mypy"
	@echo "  make all         — lint + typecheck + test"
	@echo ""
	@echo "GraphiQL: http://127.0.0.1:8010/graphql"

run:
	cd $(CURDIR) && uv run uvicorn gqlapi.main:app --reload --port 8010

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
