"""앱 설정 — pydantic-settings.

`.env` 또는 환경 변수에서 `APP_` 접두어로 로드.

운영 권장:
    - `APP_JWT_SECRET` / `APP_REFRESH_SECRET` 은 _절대_ default 사용 X. KMS / Vault / SealedSecrets.
    - `APP_DATABASE_URL` 은 docker compose 환경에서 호스트명 _컨테이너_ 기준 override.
    - `APP_CORS_ORIGINS` 는 운영 도메인만. `*` 절대 X.
    - DB 풀 (`APP_DB_POOL_*`) 은 _부하 측정 후_ 튜닝 — 부족하면 풀 고갈, 과하면 DB connection 압박.
"""

from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )

    # ── 환경 ─────────────────────────────────────────────────────
    env: str = "dev"
    log_level: str = "INFO"

    # ── DB / Cache ───────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"

    # DB 풀 — _부하 테스트 후_ 튜닝. 운영 기본값이 _이상적인 게 아님_.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800  # 30분 — 클라우드 DB idle 타임아웃 회피
    db_pool_timeout: int = 30  # 풀 고갈 시 대기 (초)

    # ── JWT (access token) ──────────────────────────────────────
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_expire_min: int = 15  # 짧게 — refresh 로 갱신

    # ── Refresh token ───────────────────────────────────────────
    refresh_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    refresh_expire_days: int = 7

    # ── Cache TTL (초) ──────────────────────────────────────────
    cache_ttl_seconds: int = 60

    # ── CORS ─────────────────────────────────────────────────────
    # 쉼표 구분 문자열을 list 로 파싱 (`APP_CORS_ORIGINS=https://a.com,https://b.com`).
    # 운영은 _명시적_ 도메인. dev 만 `["*"]` 허용.
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cors_allow_credentials: bool = True

    # ── Rate limit (login 보호) ─────────────────────────────────
    rate_limit_login_per_min: int = 10  # IP 당 분당 N회

    # ── Security 헤더 ───────────────────────────────────────────
    # `Strict-Transport-Security` — dev 에선 비활성, prod 에서 자동.
    csp_policy: str = "default-src 'self'; frame-ancestors 'none'"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: str | list[str]) -> list[str]:
        """env 변수가 _문자열_ (`a,b,c`) 로 오면 list 로 분리."""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def is_prod(self) -> bool:
        return self.env not in {"dev", "test", "local"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """싱글톤. 테스트에서 환경변수 변경 후 `get_settings.cache_clear()` 필수."""
    return Settings()
