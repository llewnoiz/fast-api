.PHONY: run test lint typecheck all curl-demo

run:
	uv run uvicorn authapp.main:app --reload --host 127.0.0.1 --port 8000

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test

# 서버 떠있을 때 (다른 터미널)
curl-demo:
	@echo "▶ /me 토큰 없이 (401)" && \
		curl -si http://localhost:8000/me | head -1
	@echo "\n▶ 로그인 (alice/alice123)" && \
		TOKEN=$$(curl -s -X POST http://localhost:8000/auth/token \
		  -H 'Content-Type: application/x-www-form-urlencoded' \
		  -d 'username=alice&password=alice123' | jq -r .access_token) && \
		echo "  token: $$TOKEN" && \
		echo "\n▶ /me (Authorization: Bearer)" && \
		curl -s http://localhost:8000/me -H "Authorization: Bearer $$TOKEN" | jq && \
		echo "\n▶ /admin/secret (alice 는 admin → 200)" && \
		curl -s http://localhost:8000/admin/secret -H "Authorization: Bearer $$TOKEN" | jq
	@echo "\n▶ bob 으로 로그인 후 /admin/secret (admin 아님 → 403)" && \
		TOKEN=$$(curl -s -X POST http://localhost:8000/auth/token \
		  -H 'Content-Type: application/x-www-form-urlencoded' \
		  -d 'username=bob&password=bob123' | jq -r .access_token) && \
		curl -si http://localhost:8000/admin/secret -H "Authorization: Bearer $$TOKEN" | head -1
	@echo "\n▶ 잘못된 비밀번호 (401)" && \
		curl -si -X POST http://localhost:8000/auth/token \
		  -H 'Content-Type: application/x-www-form-urlencoded' \
		  -d 'username=alice&password=WRONG' | head -1
