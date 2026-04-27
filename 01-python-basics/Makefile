.PHONY: run test lint typecheck demo all

# 모든 데모 스크립트 순차 실행 (Spring `gradle bootRun` 감각의 기본 명령)
run:
	@for f in src/s01_types.py src/s02_collections.py src/s03_control_flow.py \
	          src/s04_functions.py src/s05_classes.py src/s06_modules.py \
	          src/s07_unpacking.py; do \
		echo ""; \
		echo "▶ $$f"; \
		echo "─────────────────────────────────────────"; \
		uv run python $$f; \
	done

# 단일 데모 실행: make demo FILE=src/s05_classes.py
demo:
	uv run python $(FILE)

# pytest (루트 .venv 에 dev 의존성이 이미 sync 되어 있음)
test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test
