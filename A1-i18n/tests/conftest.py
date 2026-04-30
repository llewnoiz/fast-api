"""A1 fixture — TestClient (도커 / 외부 서비스 불필요)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    from i18napp.main import create_app  # noqa: PLC0415

    app = create_app()
    with TestClient(app) as c:
        yield c
