.PHONY: run test lint typecheck all demo \
        run-loop run-concurrent run-antipattern run-executor run-timeout run-iter run-loadcompare

# 모든 데모 순차 실행
run: run-loop run-concurrent run-antipattern run-executor run-timeout run-iter run-loadcompare

run-loop:
	@echo "▶ t01 event loop"        && uv run python -m asyncdeep.t01_event_loop && echo

run-concurrent:
	@echo "▶ t02 concurrent"        && uv run python -m asyncdeep.t02_concurrent && echo

run-antipattern:
	@echo "▶ t03 antipattern"       && uv run python -m asyncdeep.t03_antipattern && echo

run-executor:
	@echo "▶ t04 executor"          && uv run python -m asyncdeep.t04_executor && echo

run-timeout:
	@echo "▶ t05 timeout/cancel"    && uv run python -m asyncdeep.t05_timeout_cancel && echo

run-iter:
	@echo "▶ t06 async iter"        && uv run python -m asyncdeep.t06_async_iter && echo

run-loadcompare:
	@echo "▶ t07 fastapi load compare" && uv run python -m asyncdeep.t07_fastapi_loadcompare && echo

# 단일 모듈: make demo M=t02_concurrent
demo:
	uv run python -m asyncdeep.$(M)

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test
