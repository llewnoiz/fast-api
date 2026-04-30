.PHONY: help run test lint typecheck all clean

help:
	@echo "A9 — 파일 업로드/다운로드 (multipart / Range / presigned / chunked upload)"
	@echo ""
	@echo "  make run         — uvicorn fileio.main:app --reload --port 8009"
	@echo "  make test        — pytest"
	@echo "  make lint        — ruff check"
	@echo "  make typecheck   — mypy"
	@echo "  make all         — lint + typecheck + test"

run:
	cd $(CURDIR) && uv run uvicorn fileio.main:app --reload --port 8009

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
