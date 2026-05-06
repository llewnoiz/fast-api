# ============================================================================
# FastAPI 앱 — multi-stage 도커 이미지.
#
# 빌드 컨텍스트는 _이 디렉토리_ (`.`).
# 빌드:
#   docker build -t app:dev .
#   docker run -p 8000:8000 -e APP_DATABASE_URL=... app:dev
# 또는 compose:
#   docker compose --profile all up --build
#
# 운영 추가 권장 (본 Dockerfile 범위 밖):
#   - distroless / chainguard 이미지 (`gcr.io/distroless/python3-debian12`) — 공격 표면 ↓
#   - Trivy / Grype 같은 _보안 스캔_ CI 통합
#   - SBOM 생성 (`docker buildx build --sbom=true`)
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

# OS 보안 패치 — 빌드 시점 최신. 운영은 _주기적 재빌드_ 로 패치 보장.
# `--no-install-recommends` — 기본 추천 패키지 _제외_, 이미지 크기 ↓ 공격 표면 ↓.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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
    PYTHONPATH="/app/src" \
    APP_ENV=prod

USER app
WORKDIR /app

EXPOSE 8000

# 헬스체크 — 컨테이너 자체 동작 검증 (curl 사용 — Python 임포트 비용 없음)
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl --fail --silent --max-time 2 http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
