"""A12 fixture — 도커 / 외부 서비스 _불필요_.

학습 모드: Sentry DSN 없음 (no-op), OTel ConsoleSpanExporter, 인메모리 로그 캡처.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    from obsdeep.main import create_app  # noqa: PLC0415
    from obsdeep.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
