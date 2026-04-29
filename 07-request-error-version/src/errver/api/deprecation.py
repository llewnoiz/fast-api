"""API 버전 _Deprecation_ 헤더 — IETF draft + Sunset RFC 8594.

비교:
    Stripe API:  `Stripe-Version` 헤더로 _세분화 버전_ 관리
    GitHub API:  `Accept: application/vnd.github.v3+json` (media type 버전)
    AWS:         `X-Amz-Target` 등

여기선 _경로 기반_ (`/v1/...`, `/v2/...`) — 가장 명시적·발견 쉬움.

v1 응답에 자동으로:
    Deprecation: true
    Sunset: <RFC 1123 날짜>
    Link: </v2/orders>; rel="successor-version"
"""

from __future__ import annotations

from fastapi import Request, Response

# 학습용 — 실제론 환경 설정 또는 라우터 메타에서 읽음
SUNSET_DATE = "Sat, 31 Dec 2026 23:59:59 GMT"


def add_deprecation_headers(successor: str):
    """라우트 의존성으로 사용 — 응답에 deprecation 헤더 첨부.

    `dependencies=[Depends(add_deprecation_headers("/v2/orders"))]` 형태.
    """

    async def _dep(request: Request, response: Response) -> None:
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = SUNSET_DATE
        response.headers["Link"] = f'<{successor}>; rel="successor-version"'

    return _dep
