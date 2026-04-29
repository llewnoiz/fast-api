"""인증 관련 설정.

JWT_SECRET 은 _절대_ 코드에 박지 말 것 — 환경변수로만. 운영에선 _Secret Manager_.

비교:
    Spring:    application.yml + spring.security.oauth2 또는 jwt.secret
    NestJS:    .env + ConfigService.get('JWT_SECRET')
"""

from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    # ⚠ 학습용 _기본값_ — 운영에선 반드시 환경변수로 _랜덤한 긴 문자열_ 주입
    # `secrets.token_urlsafe(32)` 같은 걸로 한 번 만들고 비밀 저장소에.
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=30, ge=1, le=60 * 24)

    # CORS — 운영에선 _구체 origin_ 만 허용
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
