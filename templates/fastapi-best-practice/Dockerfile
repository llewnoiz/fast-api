# ============================================================================
# FastAPI 앱 — multi-stage 도커 이미지.
#
# 빌드 컨텍스트는 _이 디렉토리_ (`.`).
# 빌드:
#   docker build -t app:dev .
#   docker run -p 8000:8000 -e APP_DATABASE_URL=... app:dev
# 또는 compose:
#   docker compose --profile all up --build
# ============================================================================

# ---------- builder ----------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /build

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# 1) 의존성만 먼저 복사 → 코드 변경 시에도 _이 레이어_ 캐시 적중
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

# 2) 코드 복사 + 프로젝트 install
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# ---------- runner — 가벼운 Python ----------
FROM python:3.12-slim-bookworm AS runner

# 보안: non-root 사용자
RUN groupadd --system --gid 1000 app && \
    useradd  --system --uid 1000 --gid app --create-home --shell /bin/bash app

# builder 에서 가상환경 + 코드 복사
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/src /app/src
COPY --from=builder /build/alembic /app/alembic
COPY --from=builder /build/alembic.ini /app/alembic.ini

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src"

USER app
WORKDIR /app

EXPOSE 8000

# 헬스체크 — 컨테이너 자체 동작 검증
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz', timeout=2).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
