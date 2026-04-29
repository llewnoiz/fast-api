.PHONY: run demo test lint typecheck all \
        run-pydantic run-httpx run-orjson run-jsonpath run-datetime run-logging run-dotenv

# 모든 데모 순차 실행
run: run-pydantic run-httpx run-orjson run-jsonpath run-datetime run-logging run-dotenv

run-pydantic:
	@echo "▶ t01 pydantic" && uv run python -m libtour.t01_pydantic && echo

run-httpx:
	@echo "▶ t02 httpx" && uv run python -m libtour.t02_httpx && echo

run-orjson:
	@echo "▶ t03 orjson" && uv run python -m libtour.t03_orjson && echo

run-jsonpath:
	@echo "▶ t04 jsonpath" && uv run python -m libtour.t04_jsonpath && echo

run-datetime:
	@echo "▶ t05 datetime" && uv run python -m libtour.t05_datetime && echo

run-logging:
	@echo "▶ t06 logging" && uv run python -m libtour.t06_logging && echo

run-dotenv:
	@echo "▶ t07 dotenv" && uv run python -m libtour.t07_dotenv && echo

# 단일 모듈 빠르게: make demo M=t01_pydantic
demo:
	uv run python -m libtour.$(M)

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test
