.PHONY: test lint typecheck all build install-global uninstall-global

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

# wheel + sdist 빌드 — dist/ 에 산출물
build:
	uv build

# 다른 환경에 _전역 CLI 도구처럼_ 설치 (학습용)
install-global:
	uv tool install --from . fastapi-common

uninstall-global:
	uv tool uninstall fastapi-common
