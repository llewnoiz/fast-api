.PHONY: run test lint typecheck all migrate

run:
	uv run uvicorn tender.main:app --reload --host 127.0.0.1 --port 8000

migrate:
	uv run alembic upgrade head

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test
