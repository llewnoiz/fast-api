.PHONY: run worker test lint typecheck all

run:
	uv run uvicorn mqapp.main:app --reload --host 127.0.0.1 --port 8000

# arq 워커 — 별도 프로세스로 실행 (FastAPI 와 _독립_)
worker:
	uv run arq mqapp.arq_worker.WorkerSettings

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test
