.PHONY: run run-prod test lint typecheck all curl-demo

# 개발 서버 — auto-reload 켜짐
run:
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 운영 흉내 — workers 여러 개, reload 끔
run-prod:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

# 서버 떠 있을 때 빠르게 찔러보기 (다른 터미널에서)
curl-demo:
	@echo "▶ /healthz"  && curl -s http://localhost:8000/healthz | jq
	@echo "\n▶ /readyz"  && curl -s http://localhost:8000/readyz | jq
	@echo "\n▶ /items"   && curl -s 'http://localhost:8000/items?in_stock_only=true&limit=5' | jq
	@echo "\n▶ /items/1" && curl -s http://localhost:8000/items/1 | jq
	@echo "\n▶ /items/999 (404)" && curl -si http://localhost:8000/items/999 | head -1
	@echo "\n▶ POST /echo" && curl -s -X POST http://localhost:8000/echo \
		-H "Content-Type: application/json" \
		-d '{"message":"hi","repeat":3}' | jq
	@echo "\n▶ POST /echo (검증 실패 — 422)" && curl -si -X POST http://localhost:8000/echo \
		-H "Content-Type: application/json" \
		-d '{"message":"","repeat":99}' | head -1
