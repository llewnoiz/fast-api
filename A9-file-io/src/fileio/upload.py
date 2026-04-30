"""multipart/form-data 업로드 헬퍼 + 검증.

FastAPI 가 `UploadFile` 로 자동 파싱 — `python-multipart` 사용.
`UploadFile` 의 `.read()` 는 _전체_ 메모리 로드 → 큰 파일은 `.read(chunk)` 루프.

**검증 가이드** (보안):
    1. 크기 한도 — _전송 중_ 누적 검증 (헤더 Content-Length 신뢰 X)
    2. MIME 타입 _감지_ ── 클라이언트가 보낸 Content-Type _믿지 말 것_. 매직 바이트 검사 (`python-magic` 또는 첫 바이트).
    3. 확장자 sanitize — 클라이언트 파일명에 `..`, `/`, NUL 검사
    4. 파일 _내용_ 검사 — 이미지면 PIL.Image.verify(), PDF/zip 폭탄 검사 (decompression bomb)
    5. 안티바이러스 — ClamAV 같은 도구 (운영급, 사용자 업로드 콘텐츠)

비교:
    Spring `MultipartFile` — 검증은 직접
    NestJS `@UploadedFile()` + `FileTypeValidator` / `MaxFileSizeValidator`
    Go `multipart.Reader` — Reader 패턴
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

from fastapi import HTTPException, UploadFile

# 단순화된 화이트리스트. 운영은 _훨씬_ 엄격하게.
ALLOWED_MIME = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "application/octet-stream",  # 학습용으로 허용
}

_FILENAME_RE = re.compile(r"^[A-Za-z0-9._\-]+$")


def sanitize_filename(name: str) -> str:
    """파일명 sanitize — _서버 측_ 키로 쓰기 전에 _꼭_."""
    # 경로 구분자 제거 / NUL / 제어 문자 제거
    name = name.replace("\x00", "").split("/")[-1].split("\\")[-1]
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="invalid filename")
    if not _FILENAME_RE.match(name):
        # 허용 문자만 — 운영은 더 관대해도 OK (예: 한글 + URL 인코딩)
        raise HTTPException(status_code=400, detail="filename must be [A-Za-z0-9._-]")
    return name


async def stream_with_size_limit(
    file: UploadFile, *, max_bytes: int, chunk_bytes: int = 64 * 1024
) -> AsyncIterator[bytes]:
    """`UploadFile` 을 _청크_ 로 yield 하면서 _누적 크기_ 검증.

    Content-Length 헤더는 _신뢰 불가_ (악성 클라이언트가 거짓말 가능). 실제 바이트 카운트.
    """
    total = 0
    while True:
        chunk = await file.read(chunk_bytes)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail=f"upload exceeds {max_bytes} bytes")
        yield chunk


def assert_allowed_mime(content_type: str | None) -> None:
    """클라이언트가 보낸 Content-Type 검증 — _첫 방어선_, 더 엄격한 매직 바이트 검사 권장.

    Content-Type 이 없으면 `application/octet-stream` 로 간주.
    """
    ct = (content_type or "application/octet-stream").split(";")[0].strip()
    if ct not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"unsupported media type: {ct}")
