.PHONY: run test lint typecheck all migrate migrate-create migrate-down

# 도커 db profile 띄우기 + 마이그레이션 적용 후 서버
run:
	uv run uvicorn dbapp.main:app --reload --host 127.0.0.1 --port 8000

# 마이그레이션 — 실제 Postgres 가 떠 있어야 함 (05 의 docker compose db profile)
migrate:
	uv run alembic upgrade head

# 새 마이그레이션 _수동_ 작성용
migrate-create:
	uv run alembic revision -m "$(M)"

# 자동 생성 — 모델과 DB 비교
migrate-autogen:
	uv run alembic revision --autogenerate -m "$(M)"

migrate-down:
	uv run alembic downgrade -1

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

all: lint typecheck test
