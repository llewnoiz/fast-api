.PHONY: run run-prod test lint typecheck all curl-demo

run:
	uv run uvicorn errver.main:app --reload --host 127.0.0.1 --port 8000

run-prod:
	uv run uvicorn errver.main:app --host 0.0.0.0 --port 8000 --workers 4

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

# 서버 떠있을 때 빠르게 (다른 터미널)
curl-demo:
	@echo "▶ v1 GET /v1/orders/1 (deprecation 헤더 확인)" && \
		curl -si http://localhost:8000/v1/orders/1 | head -10
	@echo "\n▶ v2 GET /v2/orders/1" && \
		curl -s http://localhost:8000/v2/orders/1 | jq
	@echo "\n▶ v2 GET /v2/orders/999 (NOT_FOUND)" && \
		curl -s http://localhost:8000/v2/orders/999 | jq
	@echo "\n▶ v2 POST /v2/orders (검증 실패 422 — 잘못된 SKU)" && \
		curl -s -X POST http://localhost:8000/v2/orders \
		-H 'Content-Type: application/json' \
		-d '{"sku":"lower","quantity":5}' | jq
	@echo "\n▶ v2 POST /v2/orders (재고 없음 409)" && \
		curl -s -X POST http://localhost:8000/v2/orders \
		-H 'Content-Type: application/json' \
		-d '{"sku":"DISCONTINUED-001","quantity":1}' | jq
	@echo "\n▶ v2 POST /v2/orders (정상 201)" && \
		curl -s -X POST http://localhost:8000/v2/orders \
		-H 'Content-Type: application/json' \
		-d '{"sku":"PEN-002","quantity":3}' | jq
