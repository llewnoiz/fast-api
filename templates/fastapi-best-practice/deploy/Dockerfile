# ============================================================================
# deploy/Dockerfile — 운영 배포용 _명시 위치_ 이미지 정의.
#
# 본 템플릿은 _루트_ Dockerfile (개발/CI 동일) 과 `deploy/Dockerfile` (운영)
# 두 위치 모두 둠. BFF 관행: CI/CD 가 어느 쪽 보든 빌드 가능. 운영 _차이_ 가 생기면
# 이 파일에 누적 (예: distroless 베이스, SBOM 생성 옵션, 추가 ENV 등).
#
# 현재는 루트 Dockerfile 과 _동일 내용_. 운영 변경 시 여기서 분기.
# ============================================================================

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /build

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

FROM python:3.12-slim-bookworm AS runner

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1000 app && \
    useradd  --system --uid 1000 --gid app --create-home --shell /bin/bash app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/src /app/src
COPY --from=builder /build/alembic /app/alembic
COPY --from=builder /build/alembic.ini /app/alembic.ini
COPY deploy/run.sh /app/run.sh

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src" \
    APP_ENV=prod

USER app
WORKDIR /app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl --fail --silent --max-time 2 http://localhost:8000/healthz || exit 1

CMD ["/app/run.sh"]
