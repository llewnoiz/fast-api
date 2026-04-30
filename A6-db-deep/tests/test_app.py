"""FastAPI 엔드포인트 e2e 테스트."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_healthz(app_client: AsyncClient) -> None:
    r = await app_client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_seed_and_n_plus_one_endpoints(app_client: AsyncClient) -> None:
    seed_res = await app_client.post("/seed")
    assert seed_res.status_code == 200

    naive = await app_client.get("/n-plus-one/naive")
    selectin = await app_client.get("/n-plus-one/selectin")
    joined = await app_client.get("/n-plus-one/joined")

    assert naive.status_code == selectin.status_code == joined.status_code == 200
    naive_q = naive.json()["queries"]
    selectin_q = selectin.json()["queries"]
    joined_q = joined.json()["queries"]

    # naive >> selectin / joined — _패턴 효과_ 검증
    assert naive_q > selectin_q
    assert naive_q > joined_q
    assert selectin_q == 2
    assert joined_q == 1


async def test_jsonb_endpoints(app_client: AsyncClient) -> None:
    await app_client.post("/seed")

    cat = await app_client.get("/jsonb/by-category/tech")
    assert cat.status_code == 200
    # 시드는 시드 데이터 100명x10 — 시드된 _기본_ fixture (clean_tables 포함) 와는 별도라
    # 이 endpoint 호출 시점엔 데이터가 있어야 함.
    assert isinstance(cat.json()["post_ids"], list)


async def test_fts_endpoints(app_client: AsyncClient) -> None:
    await app_client.post("/seed")

    res = await app_client.get("/fts/search", params={"q": "fastapi"})
    assert res.status_code == 200
    assert isinstance(res.json()["post_ids"], list)


async def test_fts_empty_query_400(app_client: AsyncClient) -> None:
    r = await app_client.get("/fts/search", params={"q": "  "})
    assert r.status_code == 400
