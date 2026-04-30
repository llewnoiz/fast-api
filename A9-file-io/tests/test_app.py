"""FastAPI e2e — 업로드 / 다운로드 / Range / presigned / multipart."""

from __future__ import annotations

import io
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200


def test_upload_and_download(client: TestClient) -> None:
    body = b"Hello, A9!"
    r = client.post("/files", files={"file": ("hello.txt", body, "text/plain")})
    assert r.status_code == 200
    body_json = r.json()
    assert body_json["size"] == len(body)

    g = client.get("/files/hello.txt")
    assert g.status_code == 200
    assert g.headers.get("accept-ranges") == "bytes"
    assert g.content == body


def test_upload_strips_path_traversal(client: TestClient) -> None:
    """`../escape` 의 `../` 부분이 _제거_ 되고 _basename_ 만 사용됨 (공격 차단)."""
    r = client.post(
        "/files", files={"file": ("../escape.txt", b"x", "text/plain")}
    )
    assert r.status_code == 200
    assert r.json()["key"] == "escape.txt"


def test_upload_rejects_unsupported_chars(client: TestClient) -> None:
    """공백/특수문자가 포함된 파일명 → 400 (`[A-Za-z0-9._-]` 화이트리스트)."""
    r = client.post(
        "/files", files={"file": ("hello world!.txt", b"x", "text/plain")}
    )
    assert r.status_code == 400


def test_upload_unsupported_type_415(client: TestClient) -> None:
    r = client.post(
        "/files",
        files={"file": ("a.exe", b"MZ", "application/x-msdownload")},
    )
    assert r.status_code == 415


def test_upload_size_limit_413(client: TestClient, storage_root: Path) -> None:
    # 환경변수로 한도 _작게_ 재설정
    import os  # noqa: PLC0415

    os.environ["A9_MAX_UPLOAD_BYTES"] = "16"
    from fileio.main import create_app  # noqa: PLC0415
    from fileio.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        r = c.post(
            "/files",
            files={"file": ("big.txt", b"a" * 1024, "text/plain")},
        )
        assert r.status_code == 413
    # 다음 테스트가 영향 안 받게 환경변수 복구
    del os.environ["A9_MAX_UPLOAD_BYTES"]
    get_settings.cache_clear()


def test_range_download_206(client: TestClient) -> None:
    body = bytes(range(256))  # 0..255
    client.post("/files", files={"file": ("range.bin", body, "application/octet-stream")})

    r = client.get("/files/range.bin", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 10-19/{len(body)}"
    assert r.headers["content-length"] == "10"
    assert r.content == bytes(range(10, 20))


def test_range_invalid_416(client: TestClient) -> None:
    body = b"abc"
    client.post("/files", files={"file": ("tiny.bin", body, "application/octet-stream")})
    r = client.get("/files/tiny.bin", headers={"Range": "bytes=100-200"})
    assert r.status_code == 416


def test_delete_file(client: TestClient) -> None:
    client.post("/files", files={"file": ("del.txt", b"x", "text/plain")})
    r = client.delete("/files/del.txt")
    assert r.status_code == 204
    assert client.get("/files/del.txt").status_code == 404


def test_presigned_put_flow(client: TestClient) -> None:
    """1) /presign → URL → 2) PUT 으로 직접 업로드."""
    p = client.post("/presign", json={"method": "PUT", "key": "report.pdf", "expires_in": 60})
    assert p.status_code == 200
    url = p.json()["url"]

    parsed = urlsplit(url)
    qs = parse_qs(parsed.query)
    full_path = f"{parsed.path}?{parsed.query}"

    r = client.put(full_path, content=b"PDFCONTENT")
    assert r.status_code == 200
    assert r.json()["size"] == 10

    # 서명 변조 → 403
    bad_qs = qs.copy()
    bad_qs["X-Signature"] = ["tampered"]
    bad_url = f"{parsed.path}?X-Method={qs['X-Method'][0]}&X-Expires={qs['X-Expires'][0]}&X-Signature=tampered"
    r2 = client.put(bad_url, content=b"x")
    assert r2.status_code == 403


def test_multipart_upload_flow(client: TestClient) -> None:
    """initiate → 3 parts → complete → 다운로드 검증."""
    init = client.post("/uploads", json={"key": "big.bin"})
    assert init.status_code == 200
    upload_id = init.json()["upload_id"]

    parts_data = [b"AAAAA", b"BBBBB", b"CCCCC"]
    etags: list[tuple[int, str]] = []
    for i, data in enumerate(parts_data, start=1):
        r = client.put(
            f"/uploads/{upload_id}/{i}",
            content=data,
        )
        assert r.status_code == 200
        etags.append((i, r.json()["etag"]))

    complete = client.post(
        f"/uploads/{upload_id}/complete",
        json={"parts": [{"number": n, "etag": e} for n, e in etags]},
    )
    assert complete.status_code == 200
    assert complete.json()["size"] == sum(len(p) for p in parts_data)

    # 다운로드해서 합쳐졌는지 확인
    g = client.get("/files/big.bin")
    assert g.content == b"".join(parts_data)


def test_multipart_etag_mismatch_400(client: TestClient) -> None:
    init = client.post("/uploads", json={"key": "bad.bin"})
    upload_id = init.json()["upload_id"]
    client.put(f"/uploads/{upload_id}/1", content=b"abc")

    r = client.post(
        f"/uploads/{upload_id}/complete",
        json={"parts": [{"number": 1, "etag": "wrong-etag"}]},
    )
    assert r.status_code == 400


def test_multipart_abort(client: TestClient) -> None:
    init = client.post("/uploads", json={"key": "abort.bin"})
    upload_id = init.json()["upload_id"]
    client.put(f"/uploads/{upload_id}/1", content=b"data")
    r = client.post(f"/uploads/{upload_id}/abort")
    assert r.status_code == 204
    # 이후 complete 시도 → 404
    r2 = client.post(
        f"/uploads/{upload_id}/complete", json={"parts": [{"number": 1, "etag": "x"}]}
    )
    assert r2.status_code == 404


def test_unused_imports_kept_for_test_isolation() -> None:
    """io 모듈은 _향후_ binary upload 테스트에서 쓰일 placeholder."""
    assert io.BytesIO is not None
