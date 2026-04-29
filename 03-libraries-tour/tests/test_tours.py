"""03 단계 라이브러리별 핵심 동작 테스트."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from libtour.t01_pydantic import ApiResponse, Order, Range, User
from libtour.t02_httpx import make_mock_async_client, make_mock_client
from libtour.t04_jsonpath import SAMPLE, deep_merge, query_all, query_one
from libtour.t05_datetime import days_between, parse_iso_8601, to_seoul
from libtour.t07_dotenv import Settings
from pydantic import ValidationError


# ---------- t01 pydantic ----------
class TestPydantic:
    def test_basic_model(self) -> None:
        u = User(id=1, name="Alice")
        assert u.active is True   # 기본값 적용
        assert u.model_dump() == {"id": 1, "name": "Alice", "active": True}

    def test_field_constraint_violation(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Order(quantity=0, sku="abc-lower", price=10)  # quantity gt=0, sku 패턴 위반
        errors = exc_info.value.errors()
        assert len(errors) >= 2  # 최소 두 필드에서 실패

    def test_alias(self) -> None:
        # 외부 camelCase JSON
        r = ApiResponse.model_validate({"requestId": "abc", "items": ["x", "y"]})
        assert r.request_id == "abc"
        # 다시 alias 로 dump
        assert r.model_dump(by_alias=True)["requestId"] == "abc"

    def test_custom_validator(self) -> None:
        Range(start=1, end=10)        # OK
        with pytest.raises(ValidationError, match="end must be"):
            Range(start=10, end=5)


# ---------- t02 httpx ----------
class TestHttpx:
    def test_mock_sync_200(self) -> None:
        with make_mock_client() as client:
            r = client.get("/users/1")
            assert r.status_code == 200
            assert r.json() == {"id": 1, "name": "Alice"}

    def test_mock_sync_404(self) -> None:
        with make_mock_client() as client:
            r = client.get("/users/999")
            assert r.status_code == 404

    def test_mock_async_concurrent(self) -> None:
        """async + asyncio.gather — 여러 호출 _동시_ 실행 검증."""

        async def _run() -> list[dict[str, object]]:
            async with make_mock_async_client() as client:
                results = await asyncio.gather(
                    client.get("/a"),
                    client.get("/b"),
                    client.get("/c"),
                )
                return [r.json() for r in results]

        results = asyncio.run(_run())
        assert len(results) == 3
        assert results[0] == {"path": "/a"}


# ---------- t04 jsonpath + deep merge ----------
class TestJsonpath:
    def test_query_one(self) -> None:
        assert query_one(SAMPLE, "$.users[0].name") == "Alice"
        assert query_one(SAMPLE, "$.meta.page") == 1
        assert query_one(SAMPLE, "$.nonexistent") is None

    def test_query_all_filter(self) -> None:
        # 명시적 == true 필요. `?(@.active)` 만 쓰면 _존재 검사_ 가 되어 모두 매치됨 (jsonpath-ng 함정)
        active_names = query_all(SAMPLE, "$.users[?(@.active==true)].name")
        assert sorted(active_names) == ["Alice", "Carol"]

    def test_query_recursive(self) -> None:
        # `..` 는 어느 깊이든 검색
        emails = query_all(SAMPLE, "$..email")
        assert len(emails) == 3

    def test_deep_merge_preserves_nested(self) -> None:
        a = {"db": {"host": "local", "port": 5432, "pool": {"min": 1, "max": 10}}}
        b = {"db": {"host": "prod", "pool": {"max": 50}}}
        merged = deep_merge(a, b)
        # host 갱신, port 보존, pool.min 보존, pool.max 갱신
        assert merged["db"]["host"] == "prod"
        assert merged["db"]["port"] == 5432
        assert merged["db"]["pool"] == {"min": 1, "max": 50}

    def test_deep_merge_does_not_mutate_inputs(self) -> None:
        a = {"x": {"y": 1}}
        b = {"x": {"z": 2}}
        deep_merge(a, b)
        assert a == {"x": {"y": 1}}    # 원본 보존
        assert b == {"x": {"z": 2}}


# ---------- t05 datetime ----------
class TestDatetime:
    def test_iso_with_offset(self) -> None:
        dt = parse_iso_8601("2026-04-28T12:34:56+09:00")
        assert dt.tzinfo is not None
        assert dt.utcoffset().total_seconds() == 9 * 3600  # type: ignore[union-attr]

    def test_iso_naive_becomes_utc(self) -> None:
        # tz 없는 입력은 UTC 로 간주
        dt = parse_iso_8601("2026-04-28T12:00:00")
        assert dt.tzinfo == UTC

    def test_to_seoul_rejects_naive(self) -> None:
        with pytest.raises(ValueError, match="naive"):
            to_seoul(datetime(2026, 1, 1))   # tzinfo 없음

    def test_days_between(self) -> None:
        a = datetime(2026, 1, 1, tzinfo=UTC)
        b = datetime(2026, 1, 11, tzinfo=UTC)
        assert days_between(a, b) == 10
        assert days_between(b, a) == 10  # 절대값


# ---------- t07 settings ----------
class TestSettings:
    def test_loads_env_example(self) -> None:
        s = Settings()
        # .env.example 의 값
        assert s.database_url.startswith("postgresql://")
        assert s.debug is True              # 'true' → True 자동 변환
        assert s.api_timeout_ms == 3000     # 문자열 → int 자동 변환
