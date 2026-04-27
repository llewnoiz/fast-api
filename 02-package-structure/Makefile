.PHONY: run hello shout test lint typecheck build install all

# 기본 데모 — 등록된 콘솔 스크립트 호출
run: hello shout

hello:
	@echo "▶ greeter hello Alice --locale en"
	@uv run greeter hello Alice --locale en
	@echo "▶ greeter hello 앨리스"
	@uv run greeter hello 앨리스

shout:
	@echo "▶ greeter shout 'hello world'"
	@uv run greeter shout "hello world"

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

# wheel/sdist 빌드 — 14 단계의 사내 배포로 이어지는 떡밥.
build:
	uv build

# 다른 환경에 전역 CLI 로 설치하고 싶을 때 (학습용)
install:
	uv tool install --from . greeter

all: lint typecheck test
