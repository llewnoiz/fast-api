"""Items CRUD e2e — 인증 + owner 가드 + 캐시."""

from __future__ import annotations

import pytest

from tests.conftest import signup_and_login

pytestmark = pytest.mark.integration


async def test_full_crud_cycle(app_client) -> None:
    _, headers = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )

    # CREATE
    create = await app_client.post(
        "/api/v1/items",
        json={"title": "First", "description": "hello"},
        headers=headers,
    )
    assert create.status_code == 201
    body = create.json()
    assert body["code"] == "OK"
    item_id = body["data"]["id"]
    assert body["data"]["title"] == "First"
    assert body["data"]["description"] == "hello"

    # GET
    get_r = await app_client.get(f"/api/v1/items/{item_id}", headers=headers)
    assert get_r.status_code == 200
    assert get_r.json()["data"]["id"] == item_id

    # LIST (Page 응답 ── data 가 Page[T] 형식)
    list_r = await app_client.get("/api/v1/items", headers=headers)
    assert list_r.status_code == 200
    page = list_r.json()["data"]
    assert page["total"] == 1
    assert page["limit"] == 50
    assert page["offset"] == 0
    assert page["has_next"] is False
    assert len(page["items"]) == 1

    # PUT (description 만 변경)
    put_r = await app_client.put(
        f"/api/v1/items/{item_id}",
        json={"description": "updated"},
        headers=headers,
    )
    assert put_r.status_code == 200
    assert put_r.json()["data"]["description"] == "updated"
    assert put_r.json()["data"]["title"] == "First"  # 변경 안 됨

    # DELETE
    del_r = await app_client.delete(f"/api/v1/items/{item_id}", headers=headers)
    assert del_r.status_code == 200
    assert del_r.json()["message"] == "deleted"

    # GET after delete → 404
    after = await app_client.get(f"/api/v1/items/{item_id}", headers=headers)
    assert after.status_code == 404
    assert after.json()["code"] == "NOT_FOUND"


async def test_unauthenticated_blocked(app_client) -> None:
    r = await app_client.post("/api/v1/items", json={"title": "x"})
    assert r.status_code == 401


async def test_owner_guard_blocks_other_user(app_client) -> None:
    """alice 의 아이템을 bob 이 GET / PUT / DELETE → 모두 403."""
    _, alice_h = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    _, bob_h = await signup_and_login(
        app_client, email="bob@example.com", username="bob"
    )

    create = await app_client.post(
        "/api/v1/items", json={"title": "alice's"}, headers=alice_h
    )
    item_id = create.json()["data"]["id"]

    # bob 의 GET → 403
    r = await app_client.get(f"/api/v1/items/{item_id}", headers=bob_h)
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"

    # bob 의 PUT → 403
    r2 = await app_client.put(
        f"/api/v1/items/{item_id}",
        json={"title": "stolen"},
        headers=bob_h,
    )
    assert r2.status_code == 403

    # bob 의 DELETE → 403
    r3 = await app_client.delete(f"/api/v1/items/{item_id}", headers=bob_h)
    assert r3.status_code == 403


async def test_list_only_returns_own_items(app_client) -> None:
    _, alice_h = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    _, bob_h = await signup_and_login(
        app_client, email="bob@example.com", username="bob"
    )

    await app_client.post("/api/v1/items", json={"title": "alice 1"}, headers=alice_h)
    await app_client.post("/api/v1/items", json={"title": "alice 2"}, headers=alice_h)
    await app_client.post("/api/v1/items", json={"title": "bob 1"}, headers=bob_h)

    alice_list = await app_client.get("/api/v1/items", headers=alice_h)
    alice_page = alice_list.json()["data"]
    assert alice_page["total"] == 2
    assert len(alice_page["items"]) == 2

    bob_list = await app_client.get("/api/v1/items", headers=bob_h)
    bob_page = bob_list.json()["data"]
    assert bob_page["total"] == 1
    assert bob_page["items"][0]["title"] == "bob 1"


async def test_validation_short_title_422(app_client) -> None:
    _, headers = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    r = await app_client.post(
        "/api/v1/items", json={"title": ""}, headers=headers
    )
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


async def test_get_unknown_item_404(app_client) -> None:
    _, headers = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    r = await app_client.get("/api/v1/items/99999", headers=headers)
    assert r.status_code == 404


async def test_pagination(app_client) -> None:
    _, headers = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    for i in range(5):
        await app_client.post(
            "/api/v1/items", json={"title": f"item {i}"}, headers=headers
        )

    r = await app_client.get(
        "/api/v1/items", params={"limit": 2, "offset": 0}, headers=headers
    )
    page1 = r.json()["data"]
    assert len(page1["items"]) == 2
    assert page1["total"] == 5
    assert page1["has_next"] is True

    r2 = await app_client.get(
        "/api/v1/items", params={"limit": 2, "offset": 2}, headers=headers
    )
    page2 = r2.json()["data"]
    assert len(page2["items"]) == 2
    assert page2["has_next"] is True

    r3 = await app_client.get(
        "/api/v1/items", params={"limit": 10, "offset": 4}, headers=headers
    )
    page3 = r3.json()["data"]
    assert len(page3["items"]) == 1
    assert page3["has_next"] is False


async def test_cache_set_after_get(app_client) -> None:
    """GET 호출 후 Redis 에 캐시 _저장_ 되었는지 직접 검증."""
    _, headers = await signup_and_login(
        app_client, email="alice@example.com", username="alice"
    )
    create = await app_client.post(
        "/api/v1/items", json={"title": "cached"}, headers=headers
    )
    item_id = create.json()["data"]["id"]

    # 첫 GET → cache set
    await app_client.get(f"/api/v1/items/{item_id}", headers=headers)

    # Redis 에서 직접 키 조회
    import json
    import os

    from redis.asyncio import Redis

    rc = Redis.from_url(os.environ["APP_REDIS_URL"], decode_responses=True)
    raw = await rc.get(f"app:item:{item_id}")
    await rc.aclose()
    assert raw is not None
    cached = json.loads(raw)
    assert cached["id"] == item_id
    assert cached["title"] == "cached"
