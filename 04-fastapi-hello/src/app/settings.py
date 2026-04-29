"""앱 설정 — pydantic-settings 기반.

비교:
    Spring:    @ConfigurationProperties + application.yml (가장 가까움)
    NestJS:    @nestjs/config (ConfigModule + ConfigService)
    Kotlin:    Spring 동일 또는 Konf
    Node:      dotenv + 직접 파싱 (보일러플레이트 많음)

핵심:
    - 환경변수 → 자동 타입 변환 → 검증 → _불변_ 객체
    - `lru_cache` 로 _싱글톤_ 만들어 의존성 주입에 활용 (FastAPI Depends)
    - 12-factor: 코드와 설정 분리
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """앱 전체 설정.

    `.env` 또는 OS 환경변수에서 자동 로드. `APP_` 접두사를 쓰면 명확:
        APP_PORT=9000 ./run.sh
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",          # 환경변수: APP_PORT, APP_DEBUG, ...
        extra="ignore",
    )

    # 메타데이터
    app_name: str = "fastapi-hello"
    version: str = "0.1.0"
    env: Literal["dev", "staging", "prod"] = "dev"

    # 서버
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    # 동작
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # OpenAPI 문서 노출 여부 (운영에선 끄는 경우 많음)
    docs_enabled: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """싱글톤 패턴 — `Depends(get_settings)` 로 라우트에 주입.

    `lru_cache(maxsize=1)` 가 _순수 함수_ 의 결과를 캐시 → _첫 호출 시점에 한 번만_
    Settings 를 만들고 이후로는 같은 객체 재사용. Spring 의 `@Bean` 싱글톤 자리.
    """
    return Settings()
