"""S3 스타일 Multipart Upload — 큰 파일 _분할_ 업로드.

흐름:
```
1. POST /uploads          → uploadId 발급
2. PUT  /uploads/{id}/{n} → part N 업로드 (N=1..10000), ETag 반환
3. POST /uploads/{id}/complete  body=[{n,etag},...]
                          → 모든 part 를 _하나로 합침_, 최종 키 노출
   POST /uploads/{id}/abort    → 모든 part 삭제
```

**왜 multipart?**
    - 단일 PUT 보다 _병렬_ 가능 (part 별 동시 업로드)
    - 네트워크 끊겨도 _실패한 part 만_ 재전송
    - 진행률 / 일시정지 / 재개 자연 지원
    - S3 single PUT 한도 5 GiB → multipart 는 5 TiB

**S3 규약**:
    - part 5 MiB ~ 5 GiB (마지막은 5 MiB 미만 OK)
    - 최대 10,000 part
    - ETag = part 내용의 MD5

**고아 정리**:
    abort 안 된 incomplete uploads 는 _영원히_ 디스크 차지 → S3 lifecycle policy 또는 cron.

본 모듈은 _학습용 인메모리 + LocalStorage_ 결합. 운영은 S3 multipart 직접.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field

from fileio.storage import LocalStorage, StoredObject


@dataclass
class UploadPart:
    number: int
    etag: str
    size: int


@dataclass
class MultipartUpload:
    upload_id: str
    final_key: str
    parts: dict[int, UploadPart] = field(default_factory=dict)


class MultipartUploadManager:
    """진행 중인 multipart 업로드 _상태_ 관리.

    학습용 단순화: 인메모리 dict + LocalStorage 의 _서브 디렉토리_ 에 part 저장.
    운영급은: state 를 Redis/DB, part 를 S3 (S3 자체 multipart API 사용).
    """

    def __init__(self, storage: LocalStorage) -> None:
        self.storage = storage
        self.uploads: dict[str, MultipartUpload] = {}

    def initiate(self, final_key: str) -> str:
        """uploadId 발급 — 16바이트 secrets 토큰."""
        upload_id = secrets.token_urlsafe(16)
        self.uploads[upload_id] = MultipartUpload(upload_id=upload_id, final_key=final_key)
        return upload_id

    def _part_key(self, upload_id: str, number: int) -> str:
        return f".uploads/{upload_id}/part-{number:05d}"

    async def upload_part(self, upload_id: str, number: int, data: bytes) -> str:
        """part 저장 + ETag 반환. ETag = MD5 (S3 호환)."""
        if upload_id not in self.uploads:
            raise KeyError(f"unknown upload: {upload_id}")
        if number < 1 or number > 10000:
            raise ValueError("part number must be 1..10000")

        async def _gen():
            yield data

        key = self._part_key(upload_id, number)
        await self.storage.put(key, _gen())
        etag = hashlib.md5(data, usedforsecurity=False).hexdigest()
        self.uploads[upload_id].parts[number] = UploadPart(number=number, etag=etag, size=len(data))
        return etag

    async def complete(self, upload_id: str, expected_parts: list[tuple[int, str]]) -> StoredObject:
        """[(number, etag), ...] 받아 검증 후 합치기. ETag 불일치 시 ValueError."""
        upload = self.uploads.get(upload_id)
        if upload is None:
            raise KeyError(f"unknown upload: {upload_id}")

        # 검증
        for number, etag in expected_parts:
            actual = upload.parts.get(number)
            if actual is None:
                raise ValueError(f"missing part {number}")
            if actual.etag != etag:
                raise ValueError(f"etag mismatch on part {number}")

        # part 들을 _순서대로_ 읽어 최종 파일 작성
        sorted_numbers = sorted(n for n, _ in expected_parts)

        async def merged():
            for n in sorted_numbers:
                async for chunk in await self.storage.get(self._part_key(upload_id, n)):
                    yield chunk

        result = await self.storage.put(upload.final_key, merged())

        # part 정리
        for n in upload.parts:
            await self.storage.delete(self._part_key(upload_id, n))
        del self.uploads[upload_id]
        return result

    async def abort(self, upload_id: str) -> None:
        upload = self.uploads.pop(upload_id, None)
        if upload is None:
            return
        for n in upload.parts:
            await self.storage.delete(self._part_key(upload_id, n))


