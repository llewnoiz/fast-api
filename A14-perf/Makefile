.PHONY: help test lint typecheck all clean demo

help:
	@echo "A14 — 성능 / 프로파일링"
	@echo ""
	@echo "  make test        — pytest"
	@echo "  make lint        — ruff check"
	@echo "  make typecheck   — mypy"
	@echo "  make all         — lint + typecheck + test"
	@echo "  make demo        — 알고리즘 비교 데모"

test:
	cd $(CURDIR) && uv run pytest -q

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

demo:
	@uv run python -c "\
from perfdeep.algorithm_complexity import has_duplicate_quadratic, has_duplicate_set; \
from perfdeep.bench_utils import bench, faster; \
import random; \
rng = random.Random(42); \
items = [rng.randint(0, 10000) for _ in range(500)]; \
qua = bench('quadratic', lambda: has_duplicate_quadratic(items), iterations=20, warmup=2); \
set_ = bench('set', lambda: has_duplicate_set(items), iterations=20, warmup=2); \
print(f'quadratic p50: {qua.p50*1000:.3f}ms'); \
print(f'set p50:       {set_.p50*1000:.3f}ms'); \
print(f'set is {faster(set_, qua):.1f}x faster')"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
