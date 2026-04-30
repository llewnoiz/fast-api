"""Presigned URL 패턴 — _짧게 유효한_ URL 로 _직접 업로드/다운로드_.

배경:
    파일을 _앱 서버 거치지 않고_ 클라이언트가 _스토리지에 직접_ 업/다운하도록.
    이유:
        - 앱 서버 대역폭 절약 (특히 큰 파일)
        - 앱 서버를 거치면 _두 번_ 전송 — 클라이언트→앱→S3 → 비효율
        - S3 / GCS / Azure Blob 모두 같은 패턴 지원

흐름:
```
[browser] ──1) POST /presign──▶ [app] ──2) sign URL──▶ [browser]
                                                          │
[browser] ─────────3) PUT signed_url with file──────────▶ [S3]
```

서명 = HMAC. URL 에 `expires`, `key`, `signature` 가 들어있어 _서버는 stateless_ 검증.

**S3 SigV4** 와 비교:
    실제 S3 SigV4 는 헤더 / region / AccessKey / canonical request 등 _훨씬_ 복잡.
    학습용으론 _개념_ 만: HMAC + 만료 + 검증.

**다국 비교**:
    AWS SDK: `s3_client.generate_presigned_url('put_object', ...)`
    GCP: `bucket.signed_url(version='v4', ...)`
    Azure: SAS (Shared Access Signature) — 같은 개념

**보안 주의**:
    - 짧은 만료 (1~10분). 너무 길면 유출 시 위험.
    - HTTPS 필수.
    - 클라이언트 IP 제한 가능 (S3 condition policy).
    - _업로드 후_ 백엔드가 _크기/MIME/스캔_ 검증 — presigned 자체는 무결성 보장 X.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from urllib.parse import quote, urlencode


def _sign(secret: str, message: str) -> str:
    raw = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_presigned_url(
    *,
    base_url: str,
    method: str,
    key: str,
    secret: str,
    expires_in: int = 300,
    now: int | None = None,
) -> str:
    """`PUT` (upload) / `GET` (download) 용 짧은 유효 URL 생성.

    URL 모양:
        {base_url}/{key}?X-Method=PUT&X-Expires=1717000000&X-Signature=...

    검증은 _스토리지 라우트_ 에서 `verify_presigned_url` 로.
    """
    if now is None:
        now = int(time.time())
    expires = now + expires_in
    method = method.upper()
    canonical = f"{method}\n{key}\n{expires}"
    sig = _sign(secret, canonical)
    qs = urlencode({"X-Method": method, "X-Expires": expires, "X-Signature": sig})
    return f"{base_url.rstrip('/')}/{quote(key)}?{qs}"


def verify_presigned_url(
    *,
    method: str,
    key: str,
    expires: int,
    signature: str,
    secret: str,
    now: int | None = None,
) -> None:
    """검증 실패 시 `ValueError` raise. 라우트는 401/403 으로 변환."""
    if now is None:
        now = int(time.time())
    if now > expires:
        raise ValueError("url expired")
    canonical = f"{method.upper()}\n{key}\n{expires}"
    expected = _sign(secret, canonical)
    # _상수 시간_ 비교 — timing attack 방지
    if not hmac.compare_digest(expected, signature):
        raise ValueError("invalid signature")
