"""FastAPI 앱 — 파일 업로드/다운로드 / Range / presigned / multipart upload.

엔드포인트:
    GET  /healthz
    POST /files                          단순 multipart 업로드
    GET  /files/{key}                    다운로드 (Range 자동 처리, 206/200)
    DELETE /files/{key}
    POST /presign                        presigned URL 발급
    PUT  /presigned/{key}                presigned URL 검증 후 업로드 (앱 거치지 X 시뮬)
    POST /uploads                        multipart upload — initiate → uploadId
    PUT  /uploads/{id}/{number}          part 업로드
    POST /uploads/{id}/complete          parts 합치기
    POST /uploads/{id}/abort             업로드 취소
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from fileio.download import parse_range_header
from fileio.multipart_upload import MultipartUploadManager
from fileio.presigned import make_presigned_url, verify_presigned_url
from fileio.settings import get_settings
from fileio.storage import LocalStorage
from fileio.upload import (
    assert_allowed_mime,
    sanitize_filename,
    stream_with_size_limit,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    app.state.storage = LocalStorage(
        settings.storage_root, chunk_bytes=settings.download_chunk_bytes
    )
    app.state.mpm = MultipartUploadManager(app.state.storage)
    yield


def get_storage(request: Request) -> LocalStorage:
    storage: LocalStorage = request.app.state.storage
    return storage


def get_mpm(request: Request) -> MultipartUploadManager:
    mpm: MultipartUploadManager = request.app.state.mpm
    return mpm


StorageDep = Annotated[LocalStorage, Depends(get_storage)]
MPMDep = Annotated[MultipartUploadManager, Depends(get_mpm)]


class PresignIn(BaseModel):
    method: str  # "PUT" or "GET"
    key: str
    expires_in: int = 300


class CompletePart(BaseModel):
    number: int
    etag: str


class CompleteIn(BaseModel):
    parts: list[CompletePart]


def create_app() -> FastAPI:
    app = FastAPI(title="A9 — 파일 업로드/다운로드", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # ── 단순 multipart 업로드 ─────────────────────────────────
    @app.post("/files")
    async def upload_file(
        storage: StorageDep,
        file: Annotated[UploadFile, File(...)],
    ) -> dict[str, str | int]:
        settings = get_settings()
        assert_allowed_mime(file.content_type)
        filename = sanitize_filename(file.filename or "")
        stream = stream_with_size_limit(
            file,
            max_bytes=settings.max_upload_bytes,
            chunk_bytes=settings.download_chunk_bytes,
        )
        obj = await storage.put(filename, stream)
        return {"key": obj.key, "size": obj.size, "sha256": obj.sha256}

    # ── 다운로드 (+ Range) ───────────────────────────────────
    @app.get("/files/{key}")
    async def download_file(
        key: str,
        storage: StorageDep,
        range_: Annotated[str | None, Header(alias="Range")] = None,
    ) -> StreamingResponse:
        meta = await storage.stat(key)
        if meta is None:
            raise HTTPException(status_code=404, detail="not found")

        rng = parse_range_header(range_, total_size=meta.size)
        if rng is None:
            iterator = await storage.get(key)
            return StreamingResponse(
                iterator,
                status_code=200,
                headers={
                    "Content-Length": str(meta.size),
                    "Accept-Ranges": "bytes",
                    "X-Content-Type-Options": "nosniff",
                },
                media_type="application/octet-stream",
            )

        iterator = await storage.get_range(key, rng.start, rng.end)
        return StreamingResponse(
            iterator,
            status_code=206,  # Partial Content
            headers={
                "Content-Length": str(rng.length),
                "Content-Range": f"bytes {rng.start}-{rng.end}/{meta.size}",
                "Accept-Ranges": "bytes",
                "X-Content-Type-Options": "nosniff",
            },
            media_type="application/octet-stream",
        )

    @app.delete("/files/{key}", status_code=204)
    async def delete_file(key: str, storage: StorageDep) -> None:
        await storage.delete(key)

    # ── Presigned URL ─────────────────────────────────────────
    @app.post("/presign")
    async def presign(payload: PresignIn) -> dict[str, str]:
        settings = get_settings()
        if payload.method.upper() not in {"PUT", "GET"}:
            raise HTTPException(status_code=400, detail="method must be PUT or GET")
        url = make_presigned_url(
            base_url="/presigned",
            method=payload.method,
            key=payload.key,
            secret=settings.presign_secret,
            expires_in=payload.expires_in,
        )
        return {"url": url}

    @app.put("/presigned/{key}")
    async def presigned_put(
        key: str,
        storage: StorageDep,
        request: Request,
        x_method: Annotated[str | None, Query(alias="X-Method")] = None,
        x_expires: Annotated[int | None, Query(alias="X-Expires")] = None,
        x_signature: Annotated[str | None, Query(alias="X-Signature")] = None,
    ) -> dict[str, str | int]:
        settings = get_settings()
        if not (x_method and x_expires and x_signature):
            raise HTTPException(status_code=400, detail="missing presign params")
        try:
            verify_presigned_url(
                method=x_method,
                key=key,
                expires=x_expires,
                signature=x_signature,
                secret=settings.presign_secret,
            )
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e

        # 본문을 _스트리밍_ 으로 받아 쓰기 (UploadFile 안 거치고 raw body)
        async def body_iter() -> AsyncIterator[bytes]:
            async for chunk in request.stream():
                yield chunk

        obj = await storage.put(key, body_iter())
        return {"key": obj.key, "size": obj.size, "sha256": obj.sha256}

    # ── Multipart Upload (S3 호환 패턴) ────────────────────────
    @app.post("/uploads")
    async def initiate_upload(payload: dict[str, str], mpm: MPMDep) -> dict[str, str]:
        final_key = sanitize_filename(payload.get("key", ""))
        upload_id = mpm.initiate(final_key)
        return {"upload_id": upload_id}

    @app.put("/uploads/{upload_id}/{number}")
    async def upload_part(
        upload_id: str, number: int, request: Request, mpm: MPMDep
    ) -> dict[str, str]:
        body = await request.body()
        try:
            etag = await mpm.upload_part(upload_id, number, body)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"etag": etag}

    @app.post("/uploads/{upload_id}/complete")
    async def complete_upload(
        upload_id: str, payload: CompleteIn, mpm: MPMDep
    ) -> dict[str, str | int]:
        try:
            obj = await mpm.complete(upload_id, [(p.number, p.etag) for p in payload.parts])
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"key": obj.key, "size": obj.size, "sha256": obj.sha256}

    @app.post("/uploads/{upload_id}/abort", status_code=204)
    async def abort_upload(upload_id: str, mpm: MPMDep) -> None:
        await mpm.abort(upload_id)

    return app


app = create_app()
