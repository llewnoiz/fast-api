"""`python -m app` 실행 — 개발/운영 공용 엔트리.

운영은 보통 `uvicorn app.main:app --workers N` 직접 호출이 일반적이지만, BFF 컨벤션에서
`python -m app` 진입점을 _하나_ 두면 Docker CMD / IDE Run / 로컬 디버깅 모두 _동일 명령_.
"""

from __future__ import annotations

import uvicorn

from app.core.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # noqa: S104 — 컨테이너/서버 바인딩
        port=8000,
        reload=not settings.is_prod,
    )


if __name__ == "__main__":
    main()
