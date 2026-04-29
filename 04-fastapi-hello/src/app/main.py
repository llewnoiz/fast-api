"""FastAPI 앱 조립 — 04 단계의 _최종 진입점_.

비교:
    Spring Boot:  @SpringBootApplication + main()
    NestJS:       NestFactory.create(AppModule)
    Express:      const app = express(); app.use(...); app.listen()

이 파일에서:
    1. lifespan — startup/shutdown (Spring `@PostConstruct`/`@PreDestroy` 자리)
    2. FastAPI 인스턴스 생성 + 메타데이터
    3. 라우터 3개 등록
    4. ORJSONResponse 를 기본 응답 클래스로 (orjson 의 빠른 직렬화)
    5. _개발용_ 루트 진입 함수 (uvicorn 직접 실행)

실행:
    uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
또는:
    make run
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.logging_setup import configure_logging
from app.routers import echo, health, items
from app.settings import get_settings

# 참고: 옛날엔 `from fastapi.responses import ORJSONResponse` 를 default_response_class
# 로 지정해서 빠른 직렬화를 얻었지만, FastAPI 0.111+ 부터는 Pydantic 이 _직접_ JSON
# bytes 로 직렬화 → ORJSONResponse 가 deprecated 됐다. 이제 별도 설정 없이 빠름.

# ============================================================================
# lifespan — 앱 시작/종료 훅
# ============================================================================
#
# `@app.on_event("startup")` 은 _deprecated_. lifespan 컨텍스트 매니저가 표준.
#
# 내부적으로:
#   yield 이전: startup
#   yield 이후: shutdown
#
# 12 단계에서 httpx.AsyncClient / DB 풀 / Kafka 프로듀서 를 여기서 만들고 종료 시 닫음.
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001 — FastAPI 가 app 을 넘겨줌
    settings = get_settings()
    configure_logging(env=settings.env, log_level=settings.log_level)

    log = structlog.get_logger()
    log.info("app.starting", app=settings.app_name, version=settings.version, env=settings.env)
    # 여기서 외부 의존성 초기화 (DB 풀, Redis, httpx 클라이언트, Kafka 프로듀서…)

    yield

    log.info("app.stopping")
    # 여기서 정리 (close, dispose…)


# ============================================================================
# FastAPI 앱 인스턴스
# ============================================================================


def create_app() -> FastAPI:
    """app 팩토리 — 테스트 용이성을 위해 함수로 분리.

    Spring `SpringApplicationBuilder`, NestJS `NestFactory.create` 자리.
    """
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="04 단계 학습용 FastAPI 앱 — Hello / OpenAPI / 설정 관리",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    # 라우터 등록 — Spring `@RestController` 스캔 자리
    app.include_router(health.router)
    app.include_router(items.router)
    app.include_router(echo.router)

    return app


app = create_app()


# ============================================================================
# 직접 실행 진입점 (uv run python -m app.main)
# ============================================================================


def run_dev() -> None:
    """개발용 — uvicorn 을 코드로 띄움. 보통은 `make run` 또는 CLI 사용."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run_dev()
