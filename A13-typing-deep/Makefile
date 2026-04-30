.PHONY: help test lint typecheck all clean demo

help:
	@echo "A13 — Python 고급 typing & 메타프로그래밍"
	@echo ""
	@echo "  make test        — pytest"
	@echo "  make lint        — ruff check"
	@echo "  make typecheck   — mypy (가장 중요한 검증)"
	@echo "  make all         — lint + typecheck + test"
	@echo "  make demo        — 학습 모듈을 직접 import 해서 동작 확인"

test:
	cd $(CURDIR) && uv run pytest -q

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

demo:
	uv run python -c "from typingdeep.t01_generics import Box; print(Box(42).map(lambda x: x*2).get())"
	uv run python -c "from typingdeep.t06_metaclass import Plugin; print('plugins:', [p.__name__ for p in Plugin.registry])"
	uv run python -c "from typingdeep.t09_functools_advanced import fib; print('fib(30) =', fib(30))"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
