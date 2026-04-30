"""A9 설정."""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="A9_", extra="ignore")

    # 로컬 파일 저장 루트. 운영은 보통 S3 / GCS / Azure Blob.
    storage_root: Path = Field(default=Path("/tmp/a9-storage"))
    # 업로드 한도 — DoS 방지. 운영은 _훨씬 더_ 작게 + nginx client_max_body_size 와 일치.
    max_upload_bytes: int = Field(default=50 * 1024 * 1024)  # 50 MiB
    # 다운로드 청크 크기 — 메모리/속도 트레이드오프. 64 KiB ~ 1 MiB 가 일반적.
    download_chunk_bytes: int = Field(default=64 * 1024)
    # presigned URL 서명 비밀. _운영은 절대 default 쓰지 말 것_ — KMS / Vault.
    presign_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    # presigned URL TTL (초)
    presign_default_ttl: int = Field(default=300)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
