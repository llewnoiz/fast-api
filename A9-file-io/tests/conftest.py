"""A9 fixture — tmp 파일 시스템 (도커 불필요).

업로드/다운로드 패턴은 _순수 디스크_ 라 testcontainers 안 씀.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def storage_root(tmp_path: Path) -> Iterator[Path]:
    yield tmp_path / "storage"


@pytest.fixture
def client(storage_root: Path) -> Iterator[TestClient]:
    os.environ["A9_STORAGE_ROOT"] = str(storage_root)
    os.environ["A9_PRESIGN_SECRET"] = "test-secret-do-not-use-in-prod"
    from fileio.main import create_app  # noqa: PLC0415
    from fileio.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
