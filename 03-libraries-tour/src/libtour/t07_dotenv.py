"""t07 — python-dotenv + pydantic-settings: 환경변수 + 설정 관리.

비교:
    Node:        dotenv (.env), config 패키지, env-var
    Java/Spring: application.yml + @ConfigurationProperties (가장 가까움)
    Kotlin:      application.conf (HOCON) + Konf, 또는 Spring 동일
    Go:          envconfig, viper
    PHP:         vlucas/phpdotenv (Laravel 내장)

12-factor app:
    "설정은 _환경변수_ 로". 코드와 설정 분리, 컨테이너 친화.

python-dotenv:    .env 파일을 환경변수로 로드 (단순)
pydantic-settings: 환경변수를 _타입 안전한_ Settings 클래스로 (강력)

이 모듈에서:
    1. dotenv 로 단순 .env 로드
    2. pydantic-settings 로 타입 안전한 설정 — 04 단계 핵심
    3. 환경별 (dev/staging/prod) 설정 분리 패턴
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================================================
# 1) python-dotenv — .env 를 os.environ 으로 로드
# ============================================================================
#
# Node 비교:
#   require("dotenv").config()
#   process.env.DATABASE_URL
#
# Python:
#   load_dotenv()
#   os.environ["DATABASE_URL"]
#
# 단순한 사용엔 충분. 단 _타입 검증 X_ — 모든 게 문자열.
# ============================================================================


def demo_basic_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env.example"
    load_dotenv(env_path, override=True)

    db_url = os.environ.get("DATABASE_URL", "missing")
    debug = os.environ.get("DEBUG", "false")           # 문자열 — bool 변환 직접
    print(f"DATABASE_URL = {db_url}")
    print(f"DEBUG = {debug!r}  ← 문자열 'true'/'false', bool 아님")


# ============================================================================
# 2) pydantic-settings — _타입 안전한_ 환경변수
# ============================================================================
#
# Spring `@ConfigurationProperties` 와 거의 1:1.
# 환경변수 → 자동 타입 변환 → 검증 → 객체.
# 04 단계 (FastAPI Hello + 설정 관리) 에서 본격 도입.
# ============================================================================


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.example",
        env_file_encoding="utf-8",
        env_prefix="",                # APP_ 같은 접두사 가능
        extra="ignore",               # 모르는 키 무시
    )

    database_url: str = Field(default="postgresql://localhost/dev")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    api_timeout_ms: int = Field(default=5000, ge=100, le=30_000)


def demo_pydantic_settings() -> None:
    # .env.example 자동 로드 + os.environ 자동 읽기
    settings = Settings()
    print("타입 안전한 설정 객체:")
    print(f"  database_url   = {settings.database_url}")
    print(f"  debug (bool)   = {settings.debug}    ← 'true'→True 자동 변환")
    print(f"  log_level      = {settings.log_level}")
    print(f"  api_timeout_ms = {settings.api_timeout_ms}  ← int 자동 변환 + 범위 검증")


# ============================================================================
# 3) 환경별 설정 분리 — 가장 흔한 실무 패턴
# ============================================================================
#
# .env                 (공통 기본값, 커밋 X)
# .env.example         (예시, 커밋 O — 팀 공유)
# .env.local           (개발자 개인 오버라이드, 커밋 X)
# .env.production      (배포 시 secret manager 가 주입, 커밋 X)
#
# pydantic-settings 의 env_file 인자에 _목록_ 넘기면 순서대로 로드 (뒤가 이김).
# ============================================================================


def main() -> None:
    print("=== 1) python-dotenv 단순 로드 ===")
    demo_basic_dotenv()

    print("\n=== 2) pydantic-settings 타입 안전 ===")
    demo_pydantic_settings()


if __name__ == "__main__":
    main()
