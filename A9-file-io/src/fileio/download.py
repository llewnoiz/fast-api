"""다운로드 — `StreamingResponse` + HTTP `Range` (resume).

**StreamingResponse vs FileResponse**:
    - **`FileResponse(path)`** — 동기 sendfile / 메모리 매핑, 가장 빠름. 정적 파일.
    - **`StreamingResponse(generator)`** — async 청크. 동적 콘텐츠 / S3 등 외부 스토리지.

**HTTP Range** (RFC 7233):
    클라이언트가 `Range: bytes=1024-2047` 보내면 서버는 _그 부분만_ + `206 Partial Content`.
    유튜브 / mp4 player / 큰 zip 다운로드 재개에 필수.

    응답 헤더:
        HTTP/1.1 206 Partial Content
        Content-Range: bytes 1024-2047/10240        ← 단위/시작-끝/전체
        Content-Length: 1024
        Accept-Ranges: bytes

**보안**:
    - `Content-Disposition: attachment; filename="..."` 으로 _브라우저 다운로드_ 강제
    - 파일명 RFC 5987 인코딩 — `filename*=UTF-8''...` (한글/공백/특수문자)
    - `X-Content-Type-Options: nosniff` — MIME 스니핑 차단

비교:
    Node `res.setHeader('Content-Range', ...)` 직접
    Spring `ResourceRegion` + ResourceHttpRequestHandler 자동
    Go http.ServeContent — Range 자동 처리
"""

from __future__ import annotations

import re
from typing import NamedTuple

from fastapi import HTTPException

_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class ByteRange(NamedTuple):
    start: int
    end: int  # 포함

    @property
    def length(self) -> int:
        return self.end - self.start + 1


def parse_range_header(header: str | None, *, total_size: int) -> ByteRange | None:
    """`Range: bytes=START-END` 파싱. 없거나 잘못되면 None / 416 발생.

    지원:
        bytes=0-499        ← 처음 500 바이트
        bytes=500-         ← 500 부터 끝까지
        bytes=-500         ← 마지막 500 바이트 (suffix range)

    미지원 (학습 단순화):
        bytes=0-100,200-300  multi-range — 운영은 multipart/byteranges 응답 필요
    """
    if header is None:
        return None
    m = _RANGE_RE.match(header.strip())
    if not m:
        # 형식 자체가 깨짐 — 표준은 무시 (전체 응답) 권장. 학습용으로 명시적 에러.
        raise HTTPException(status_code=416, detail="malformed Range")
    s, e = m.group(1), m.group(2)
    if s == "" and e == "":
        raise HTTPException(status_code=416, detail="empty Range")
    if s == "":
        # suffix: bytes=-N
        suffix = int(e)
        if suffix == 0:
            raise HTTPException(status_code=416, detail="zero suffix")
        start = max(0, total_size - suffix)
        end = total_size - 1
    else:
        start = int(s)
        end = int(e) if e else total_size - 1
    if start > end or start >= total_size:
        raise HTTPException(
            status_code=416,
            detail="Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{total_size}"},
        )
    end = min(end, total_size - 1)
    return ByteRange(start=start, end=end)
