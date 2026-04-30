"""Presigned URL 단위 테스트."""

from __future__ import annotations

import pytest
from fileio.presigned import make_presigned_url, verify_presigned_url


def test_make_and_verify() -> None:
    secret = "s3cr3t"
    url = make_presigned_url(
        base_url="/files", method="PUT", key="report.pdf", secret=secret, expires_in=300
    )
    assert "X-Method=PUT" in url
    assert "X-Expires=" in url
    assert "X-Signature=" in url

    # parse from URL — 학습용 단순 추출
    from urllib.parse import parse_qs, urlsplit  # noqa: PLC0415

    qs = parse_qs(urlsplit(url).query)
    verify_presigned_url(
        method="PUT",
        key="report.pdf",
        expires=int(qs["X-Expires"][0]),
        signature=qs["X-Signature"][0],
        secret=secret,
    )  # raises on failure


def test_expired() -> None:
    with pytest.raises(ValueError, match="expired"):
        verify_presigned_url(
            method="PUT", key="k", expires=1, signature="bogus", secret="s", now=1000
        )


def test_invalid_signature() -> None:
    secret = "s3cr3t"
    url = make_presigned_url(
        base_url="/files", method="PUT", key="report.pdf", secret=secret
    )
    from urllib.parse import parse_qs, urlsplit  # noqa: PLC0415

    qs = parse_qs(urlsplit(url).query)
    with pytest.raises(ValueError, match="invalid"):
        verify_presigned_url(
            method="PUT",
            key="report.pdf",
            expires=int(qs["X-Expires"][0]),
            signature="tampered",
            secret=secret,
        )


def test_method_mismatch_invalid() -> None:
    secret = "s"
    url = make_presigned_url(base_url="/files", method="PUT", key="k", secret=secret)
    from urllib.parse import parse_qs, urlsplit  # noqa: PLC0415

    qs = parse_qs(urlsplit(url).query)
    with pytest.raises(ValueError):
        verify_presigned_url(
            method="GET",  # 서명한 것은 PUT
            key="k",
            expires=int(qs["X-Expires"][0]),
            signature=qs["X-Signature"][0],
            secret=secret,
        )
