"""구조화 로그의 민감정보 redact 검증."""

from __future__ import annotations

from obsdeep.structured_logging import _redact_sensitive


def test_redacts_password() -> None:
    out = _redact_sensitive(None, "info", {"user": "alice", "password": "secret123"})
    assert out["password"] == "***REDACTED***"
    assert out["user"] == "alice"


def test_redacts_authorization_header() -> None:
    out = _redact_sensitive(None, "info", {"Authorization": "Bearer xyz"})
    assert out["Authorization"] == "***REDACTED***"


def test_redacts_substring_match() -> None:
    """`api_key_v2` 같이 _부분 일치_ 도 마스킹."""
    out = _redact_sensitive(None, "info", {"api_key_v2": "k_abc"})
    assert out["api_key_v2"] == "***REDACTED***"


def test_does_not_redact_normal_keys() -> None:
    out = _redact_sensitive(None, "info", {"user_id": 1, "elapsed_ms": 50})
    assert out["user_id"] == 1
    assert out["elapsed_ms"] == 50
