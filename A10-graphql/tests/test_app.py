"""FastAPI + Strawberry 통합 e2e — HTTP POST 로 GraphQL 쿼리."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200


def test_graphql_endpoint_query(client: TestClient) -> None:
    r = client.post(
        "/graphql",
        json={"query": "{ users { name } }"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "errors" not in body or body["errors"] is None
    assert len(body["data"]["users"]) == 3


def test_graphql_with_variables(client: TestClient) -> None:
    r = client.post(
        "/graphql",
        json={
            "query": "query Q($id: Int!) { user(id: $id) { name email } }",
            "variables": {"id": 2},
        },
    )
    assert r.status_code == 200
    assert r.json()["data"]["user"]["name"] == "Bob"


def test_mutation_create_post(client: TestClient) -> None:
    r = client.post(
        "/graphql",
        json={
            "query": (
                "mutation M($input: CreatePostInput!) { "
                "createPost(input: $input) { id title author { name } } }"
            ),
            "variables": {"input": {"authorId": 1, "title": "via API", "body": "..."}},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["createPost"]["title"] == "via API"
    assert body["data"]["createPost"]["author"]["name"] == "Alice"


def test_mutation_unknown_author_returns_errors(client: TestClient) -> None:
    """GraphQL 의 _부분_ 실패 모델 — HTTP 200 + body 의 `errors`."""
    r = client.post(
        "/graphql",
        json={
            "query": (
                "mutation M($input: CreatePostInput!) { "
                "createPost(input: $input) { id } }"
            ),
            "variables": {"input": {"authorId": 9999, "title": "x", "body": "y"}},
        },
    )
    assert r.status_code == 200  # GraphQL 은 errors 도 200
    body = r.json()
    assert body["errors"] is not None
    assert "unknown author_id" in body["errors"][0]["message"]


def test_admin_stats_and_reset(client: TestClient) -> None:
    # 쿼리 한 번 → 카운터 증가
    client.post("/graphql", json={"query": "{ posts { author { name } } }"})

    stats = client.get("/admin/stats").json()
    # DataLoader 기본 켜짐 → batch 1 번
    assert stats["users_by_ids_calls"] >= 1
    assert stats["use_dataloader"] is True

    client.post("/admin/reset-stats")
    after = client.get("/admin/stats").json()
    assert after["users_by_ids_calls"] == 0


def test_dataloader_toggle(client: TestClient) -> None:
    """관리자 토글 후 다음 쿼리는 _naive_ 로 동작 → 카운터 증가폭 차이."""
    # 1) DataLoader on (기본)
    client.post("/admin/reset-stats")
    client.post("/graphql", json={"query": "{ posts { author { name } } }"})
    on_stats = client.get("/admin/stats").json()
    on_calls = on_stats["users_by_ids_calls"]

    # 2) Toggle off
    toggle = client.post("/admin/toggle-dataloader").json()
    assert toggle["use_dataloader"] is False

    client.post("/admin/reset-stats")
    client.post("/graphql", json={"query": "{ posts { author { name } } }"})
    off_stats = client.get("/admin/stats").json()
    off_calls = off_stats["users_by_ids_calls"]

    # naive 쪽 호출이 _훨씬_ 많아야 (post 7 개)
    assert off_calls > on_calls
