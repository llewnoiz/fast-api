"""테스트 fixture — testcontainers Postgres + Redis + asgi-lifespan.

학습 메모: testcontainers _ryuk_ (정리 컨테이너) 가 macOS 환경에서 가끔 포트 충돌 →
import 전에 비활성화. `with` 컨텍스트가 정리 보장.
"""

from __future__ import annotations

import os

# testcontainers ryuk 비활성화 — _import 전_ 설정 필수
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

import subprocess  # noqa: E402
import sys  # noqa: E402
from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402


def _docker_available() -> bool:
    try:
        import docker  # noqa: PLC0415

        docker.from_env(timeout=2).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


DOCKER_OK = _docker_available()


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[tuple[str, str]]:
    if not DOCKER_OK:
        pytest.skip("도커 데몬 없음")
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        async_url = (
            f"postgresql+asyncpg://{pg.username}:{pg.password}@{host}:{port}/{pg.dbname}"
        )
        sync_url = (
            f"postgresql+psycopg://{pg.username}:{pg.password}@{host}:{port}/{pg.dbname}"
        )

        # Alembic 마이그레이션 자동 적용
        cwd = Path(__file__).resolve().parent.parent
        env = {**os.environ, "ALEMBIC_DATABASE_URL": sync_url}
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"alembic 실패: {result.stderr}\n{result.stdout}")
        yield async_url, sync_url


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    if not DOCKER_OK:
        pytest.skip("도커 데몬 없음")
    from testcontainers.redis import RedisContainer  # noqa: PLC0415

    with RedisContainer("redis:7-alpine") as r:
        host = r.get_container_host_ip()
        port = r.get_exposed_port(6379)
        yield f"redis://{host}:{port}"


@pytest_asyncio.fixture
async def app_client(
    postgres_container: tuple[str, str], redis_url: str
):
    """FastAPI + 진짜 Postgres + 진짜 Redis. 매 테스트마다 _격리_ (TRUNCATE)."""
    from asgi_lifespan import LifespanManager  # noqa: PLC0415
    from httpx import ASGITransport, AsyncClient  # noqa: PLC0415

    async_url, _ = postgres_container

    # env 변수 → Settings 재로드
    os.environ["APP_DATABASE_URL"] = async_url
    os.environ["APP_REDIS_URL"] = redis_url

    from app.core.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()

    # 매 테스트 격리 ── TRUNCATE
    from sqlalchemy import text  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    eng = create_async_engine(async_url)
    sm = async_sessionmaker(eng, expire_on_commit=False)
    async with sm() as s:
        await s.execute(text("TRUNCATE users, items RESTART IDENTITY CASCADE"))
        await s.commit()
    await eng.dispose()

    # Redis 도 비우기
    from redis.asyncio import Redis  # noqa: PLC0415

    rc = Redis.from_url(redis_url, decode_responses=True)
    await rc.flushdb()
    await rc.aclose()

    from app.main import create_app  # noqa: PLC0415

    app = create_app()
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac,
    ):
        yield ac


# ── 테스트 헬퍼 ────────────────────────────────────────────────


async def signup_user(
    client,
    *,
    email: str,
    username: str,
    password: str = "password123",
) -> dict:
    r = await client.post(
        "/api/v1/users",
        json={"email": email, "username": username, "password": password},
    )
    assert r.status_code == 201, f"signup 실패: {r.text}"
    return r.json()["data"]


async def login_user(client, *, email: str, password: str = "password123") -> str:
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, f"login 실패: {r.text}"
    return r.json()["data"]["access_token"]


async def signup_and_login(
    client, *, email: str, username: str, password: str = "password123"
) -> tuple[dict, dict]:
    """편의 헬퍼 ── (user_dict, headers) 반환."""
    user = await signup_user(
        client, email=email, username=username, password=password
    )
    token = await login_user(client, email=email, password=password)
    return user, {"Authorization": f"Bearer {token}"}
