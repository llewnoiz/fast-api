.PHONY: help run test lint typecheck all clean

help:
	@echo "A12 — 관측가능성 운영급 (Sentry / 구조화 로그 / OTel / SLO / Grafana / Alertmanager)"
	@echo ""
	@echo "  make run         — uvicorn ... --port 8012"
	@echo "  make test        — pytest"
	@echo "  make lint / typecheck / all"

run:
	cd $(CURDIR) && uv run uvicorn obsdeep.main:app --reload --port 8012

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
