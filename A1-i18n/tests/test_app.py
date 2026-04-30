"""FastAPI e2e — 미들웨어가 헤더 → locale 자동 적용."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200


def test_greet_default_english(client: TestClient) -> None:
    """헤더 없으면 default (en)."""
    r = client.get("/greet", params={"name": "alice"})
    assert r.status_code == 200
    assert "Hello" in r.json()["message"]
    assert r.headers.get("content-language") == "en"


def test_greet_korean(client: TestClient) -> None:
    r = client.get(
        "/greet",
        params={"name": "alice"},
        headers={"accept-language": "ko-KR,ko;q=0.9"},
    )
    assert "안녕" in r.json()["message"]
    assert r.headers["content-language"] == "ko"


def test_greet_japanese(client: TestClient) -> None:
    r = client.get(
        "/greet", params={"name": "alice"}, headers={"accept-language": "ja"}
    )
    assert "こんにちは" in r.json()["message"]


def test_cookie_overrides_accept_language(client: TestClient) -> None:
    """쿠키 _우선_ — 사용자 선택 영구화."""
    r = client.get(
        "/greet",
        params={"name": "alice"},
        headers={"accept-language": "en"},
        cookies={"locale": "ko"},
    )
    assert "안녕" in r.json()["message"]


def test_items_singular(client: TestClient) -> None:
    r = client.get("/items", params={"n": 1}, headers={"accept-language": "en"})
    assert r.json()["message"] == "1 item"


def test_items_plural(client: TestClient) -> None:
    r = client.get("/items", params={"n": 5}, headers={"accept-language": "en"})
    assert r.json()["message"] == "5 items"


def test_validation_error_korean(client: TestClient) -> None:
    """Pydantic 검증 실패 → 한국어 에러 메시지."""
    r = client.post(
        "/orders",
        json={},
        headers={"accept-language": "ko"},
    )
    assert r.status_code == 400
    body = r.json()
    errors = body.get("detail", body).get("errors", [])
    assert len(errors) > 0
    assert any("필수" in e["message"] for e in errors)


def test_money_korean(client: TestClient) -> None:
    r = client.get(
        "/money",
        params={"amount": 1234, "cur": "KRW"},
        headers={"accept-language": "ko"},
    )
    assert "1,234" in r.json()["formatted"]


def test_money_usd_english(client: TestClient) -> None:
    r = client.get(
        "/money",
        params={"amount": 1234.56, "cur": "USD"},
        headers={"accept-language": "en"},
    )
    assert "1,234.56" in r.json()["formatted"]


def test_lang_endpoint(client: TestClient) -> None:
    r = client.get("/lang", headers={"accept-language": "ko"})
    body = r.json()
    assert body["locale"] == "ko"
    assert "한국" in body["display_self"]
    assert body["display_en"] == "Korean"
