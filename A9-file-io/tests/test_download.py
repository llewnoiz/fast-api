"""Range 헤더 파싱 테스트."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fileio.download import parse_range_header


def test_no_header_returns_none() -> None:
    assert parse_range_header(None, total_size=100) is None


def test_full_range() -> None:
    r = parse_range_header("bytes=0-99", total_size=100)
    assert r is not None
    assert (r.start, r.end, r.length) == (0, 99, 100)


def test_partial_range() -> None:
    r = parse_range_header("bytes=10-19", total_size=100)
    assert r is not None
    assert (r.start, r.end, r.length) == (10, 19, 10)


def test_open_ended_range() -> None:
    r = parse_range_header("bytes=50-", total_size=100)
    assert r is not None
    assert (r.start, r.end) == (50, 99)


def test_suffix_range() -> None:
    """`bytes=-N` — 마지막 N 바이트."""
    r = parse_range_header("bytes=-20", total_size=100)
    assert r is not None
    assert (r.start, r.end) == (80, 99)


def test_range_clamped_to_size() -> None:
    r = parse_range_header("bytes=50-999", total_size=100)
    assert r is not None
    assert r.end == 99


def test_invalid_range_416() -> None:
    with pytest.raises(HTTPException) as exc:
        parse_range_header("bytes=200-300", total_size=100)
    assert exc.value.status_code == 416


def test_malformed_range() -> None:
    with pytest.raises(HTTPException) as exc:
        parse_range_header("invalid", total_size=100)
    assert exc.value.status_code == 416


def test_empty_range() -> None:
    with pytest.raises(HTTPException):
        parse_range_header("bytes=-", total_size=100)
