"""스토리지 추상 — 학습용 LocalStorage.

운영은 _S3 호환_ (boto3 / aioboto3 / s3fs) 또는 GCS / Azure Blob.
인터페이스를 분리해두면 _개발은 LocalStorage, 운영은 S3Storage_ 로 교체 가능.

비교:
    Spring Cloud AWS S3Template
    NestJS @aws-sdk/client-s3
    Go AWS SDK v2 — 같은 패턴
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import aiofiles


@dataclass(frozen=True)
class StoredObject:
    """저장된 객체 메타. 실제 데이터는 별도 read."""

    key: str
    size: int
    sha256: str


class Storage(Protocol):
    """파일 저장소 추상. S3 호환 메서드 셋만."""

    async def put(self, key: str, data: AsyncIterator[bytes]) -> StoredObject: ...
    async def get(self, key: str) -> AsyncIterator[bytes]: ...
    async def get_range(self, key: str, start: int, end: int) -> AsyncIterator[bytes]: ...
    async def stat(self, key: str) -> StoredObject | None: ...
    async def delete(self, key: str) -> None: ...


class LocalStorage:
    """파일 시스템 기반. 학습/개발 친화. 운영은 _절대_ 단일 노드 디스크 X (HA 없음)."""

    def __init__(self, root: Path, *, chunk_bytes: int = 64 * 1024) -> None:
        self.root = root
        self.chunk_bytes = chunk_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # 키 sanitize — `..` traversal 방지. 운영급은 더 엄격 (alphanumeric + sep 만 허용).
        if ".." in key or key.startswith("/"):
            raise ValueError(f"invalid key: {key}")
        return self.root / key

    async def put(self, key: str, data: AsyncIterator[bytes]) -> StoredObject:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # _임시 파일_ 에 쓰고 _atomic rename_ — 부분 업로드가 _최종 키_ 에 노출되지 않도록.
        tmp = path.with_suffix(path.suffix + ".part")
        hasher = hashlib.sha256()
        size = 0
        try:
            async with aiofiles.open(tmp, "wb") as f:
                async for chunk in data:
                    hasher.update(chunk)
                    size += len(chunk)
                    await f.write(chunk)
            os.replace(tmp, path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                tmp.unlink()
            raise
        return StoredObject(key=key, size=size, sha256=hasher.hexdigest())

    async def get(self, key: str) -> AsyncIterator[bytes]:
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return self._iter_bytes(path, 0, path.stat().st_size - 1)

    async def get_range(self, key: str, start: int, end: int) -> AsyncIterator[bytes]:
        """`start..end` _포함_ 바이트 범위 (HTTP Range 의미와 동일)."""
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return self._iter_bytes(path, start, end)

    async def _iter_bytes(self, path: Path, start: int, end: int) -> AsyncIterator[bytes]:
        async with aiofiles.open(path, "rb") as f:
            await f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = await f.read(min(self.chunk_bytes, remaining))
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    async def stat(self, key: str) -> StoredObject | None:
        path = self._path(key)
        if not path.exists():
            return None
        size = path.stat().st_size
        # sha256 _다시_ 계산 — 운영은 metadata DB 에 저장해 캐시.
        hasher = hashlib.sha256()
        async with aiofiles.open(path, "rb") as f:
            while chunk := await f.read(self.chunk_bytes):
                hasher.update(chunk)
        return StoredObject(key=key, size=size, sha256=hasher.hexdigest())

    async def delete(self, key: str) -> None:
        path = self._path(key)
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
