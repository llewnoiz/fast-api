.PHONY: help run test lint typecheck all clean demo

help:
	@echo "A1 — 다국어 (i18n) — Accept-Language / gettext / Pydantic / Babel"
	@echo ""
	@echo "  make run         — uvicorn ... --port 8001"
	@echo "  make test        — pytest"
	@echo "  make lint / typecheck / all"

run:
	cd $(CURDIR) && uv run uvicorn i18napp.main:app --reload --port 8001

test:
	cd $(CURDIR) && uv run pytest -q

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

demo:
	@uv run python -c "\
from i18napp.catalog import gettext; \
print('en:', gettext('greeting', locale='en', name='alice')); \
print('ko:', gettext('greeting', locale='ko', name='alice')); \
print('ja:', gettext('greeting', locale='ja', name='alice'))"
	@uv run python -c "\
from i18napp.babel_setup import format_money; \
print('USD/en:', format_money(1234.56, 'USD', 'en')); \
print('KRW/ko:', format_money(1234, 'KRW', 'ko')); \
print('EUR/de:', format_money(1234.56, 'EUR', 'de'))"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
