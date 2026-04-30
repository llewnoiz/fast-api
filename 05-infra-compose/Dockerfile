# ============================================================================
# 04-fastapi-hello 를 _컨테이너_ 로 띄우는 multi-stage Dockerfile.
#
# 빌드 컨텍스트는 _리포 루트_ (`.`) — 04 디렉토리 + 워크스페이스 루트의
# pyproject.toml + uv.lock 이 모두 필요해서.
#
# 빌드:
#   docker build -f 05-infra-compose/Dockerfile -t fast-api-learning/hello:dev .
# 또는 compose 가 알아서:
#   docker compose --profile app build
# ============================================================================

# ---------- builder stage ----------
# uv 공식 이미지 (Python 3.12 미리 포함) → 의존성 _빠르게_ 해결
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /build

# uv 설정 — 컨테이너 안에선 가상환경 만들지 않고 시스템 site-packages 에 설치
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# 1) 의존성만 먼저 복사 → 이 레이어는 _코드 변경 시에도 캐시 적중_
COPY pyproject.toml uv.lock ./
COPY 04-fastapi-hello/pyproject.toml ./04-fastapi-hello/
COPY 01-python-basics/pyproject.toml ./01-python-basics/
COPY 02-package-structure/pyproject.toml ./02-package-structure/
COPY 03-libraries-tour/pyproject.toml ./03-libraries-tour/

# 워크스페이스 멤버는 install 시 build 가 필요해서 _코드_ 가 있어야 함.
# 학습용 단순화: 04 만 install 대상.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-workspace

# 2) 코드 복사 + 04 패키지 install (편집 가능 모드 X)
COPY 04-fastapi-hello/ ./04-fastapi-hello/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --package fastapi-hello

# ---------- runner stage — 가벼운 Python 3.12 ----------
FROM python:3.14-slim-bookworm AS runner

# 보안: non-root 사용자
RUN groupadd --system --gid 1000 app && \
    useradd  --system --uid 1000 --gid app --create-home --shell /bin/bash app

# uv builder 가 만든 가상환경 + 04 코드 가져오기
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/04-fastapi-hello/src /app/src

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

USER app
WORKDIR /app/src

EXPOSE 8000

# 헬스체크 — 컨테이너 자체 동작 검증
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; \
                   sys.exit(0 if urllib.request.urlopen(f'http://localhost:{__import__(\"os\").environ.get(\"APP_PORT\",\"8000\")}/healthz', timeout=2).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
