# A9 — 파일 업로드 / 다운로드

운영 파일 IO 5가지 패턴: multipart 업로드, Range 다운로드, presigned URL, S3 호환 multipart upload.

## 학습 목표

- **multipart/form-data 업로드** — `UploadFile`, 검증 (크기/MIME/파일명)
- **`StreamingResponse`** — 청크 단위 다운로드
- **HTTP `Range`** — `206 Partial Content`, 다운로드 _재개_, 비디오 seek
- **Presigned URL** — _짧게 유효한_ HMAC URL, 앱 거치지 않고 직접 업/다운
- **S3 Multipart Upload** — initiate / part / complete / abort

## 디렉토리

```
A9-file-io/
├── pyproject.toml
├── Makefile
├── README.md
├── src/fileio/
│   ├── __init__.py
│   ├── settings.py            # storage_root / max_upload_bytes / presign_secret
│   ├── storage.py             # LocalStorage (atomic put + Range get)
│   ├── upload.py              # sanitize_filename / stream_with_size_limit / MIME 검증
│   ├── download.py            # parse_range_header (RFC 7233)
│   ├── presigned.py           # HMAC-SHA256 sign / verify
│   ├── multipart_upload.py    # MultipartUploadManager (S3 호환 패턴)
│   └── main.py                # FastAPI 앱
└── tests/
    ├── conftest.py            # tmp_path 기반 — 도커 불필요
    ├── test_storage.py        # atomic rename / Range / traversal 차단
    ├── test_download.py       # Range 파싱 (suffix / open-ended / 416)
    ├── test_presigned.py      # 만료 / 변조 / method mismatch
    └── test_app.py            # FastAPI e2e (multipart, presigned, multipart upload)
```

## 실행

```bash
cd A9-file-io
make all          # ruff + mypy + 33 tests
make run          # http://127.0.0.1:8009/docs
```

## 1) 단순 multipart 업로드

```python
@app.post("/files")
async def upload_file(
    storage: StorageDep,
    file: Annotated[UploadFile, File(...)],
):
    assert_allowed_mime(file.content_type)
    filename = sanitize_filename(file.filename or "")
    stream = stream_with_size_limit(file, max_bytes=settings.max_upload_bytes)
    return await storage.put(filename, stream)
```

**핵심**:
- `UploadFile.read(N)` 으로 _청크 단위_ ── `.read()` 만 쓰면 _전체_ 메모리 로드
- `stream_with_size_limit` ── _누적 카운트_ 로 크기 검증 (Content-Length 신뢰 X)
- atomic write ── `.part` 임시 파일 + `os.replace()` (실패 시 최종 키 노출 X)

## 2) StreamingResponse + HTTP Range

```python
GET /files/big.mp4 HTTP/1.1
Range: bytes=1024-2047

HTTP/1.1 206 Partial Content
Content-Range: bytes 1024-2047/10485760
Content-Length: 1024
Accept-Ranges: bytes
```

**Range 변형**:
| 헤더 | 의미 |
|---|---|
| `bytes=0-499` | 처음 500 바이트 |
| `bytes=500-` | 500 부터 끝까지 |
| `bytes=-100` | _마지막_ 100 바이트 (suffix range) |
| `bytes=0-100,200-300` | multi-range — 본 모듈은 미지원 |

**Range 가 필요한 곳**:
- 비디오 / 오디오 seek (`<video>` 태그)
- 큰 zip / iso 다운로드 _재개_
- HTTP/2 push, CDN 캐싱

## 3) Presigned URL — 앱 서버 우회

```
[browser] ──1) POST /presign──▶ [app]
                                  │ HMAC sign(method, key, expires)
                                  ▼
[browser] ◀──2) signed URL──── [app]
   │
   └─3) PUT signed_url ──▶ [storage]   ← 앱 거치지 않음
```

**왜 필요?**:
- 앱 서버 _대역폭_ 절약 (특히 큰 파일)
- 두 번 전송 (browser→app→S3) → 비효율
- S3 / GCS / Azure Blob _모두_ 지원

**서명 = HMAC-SHA256**:
```
canonical = "PUT\nreport.pdf\n1717000000"
signature = HMAC_SHA256(secret, canonical)
url = /files/report.pdf?X-Method=PUT&X-Expires=1717000000&X-Signature=...
```

**보안**:
- 짧은 만료 (1~10분)
- HTTPS 필수
- _상수 시간_ 비교 (`hmac.compare_digest`) — timing attack 방지
- 업로드 _후_ 백엔드 검증 (크기/MIME/AV 스캔)

**다국 비교**:
```python
# 실제 운영 — boto3
s3 = boto3.client("s3")
url = s3.generate_presigned_url("put_object", Params={"Bucket": "b", "Key": "k"}, ExpiresIn=300)

# GCP
bucket = gcs.bucket("b")
url = bucket.blob("k").generate_signed_url(version="v4", expiration=300)

# Azure SAS
sas = generate_blob_sas(account_name=..., permission=BlobSasPermissions(write=True), expiry=...)
```

## 4) S3 Multipart Upload — 큰 파일 분할

```
1. POST /uploads               → uploadId
2. PUT  /uploads/{id}/{n}      → ETag (각 part)
3. POST /uploads/{id}/complete → final 파일
   POST /uploads/{id}/abort    → 모든 part 정리
```

**왜?**:
- 단일 PUT 한도 (S3 5 GiB) → multipart 5 TiB
- _병렬_ 업로드 가능
- 네트워크 끊겨도 _실패한 part 만_ 재전송
- 진행률 / 일시정지 / 재개

**S3 규약**:
- part 5 MiB ~ 5 GiB (마지막은 더 작아도 OK)
- 최대 10,000 part
- ETag = part 의 MD5 (single PUT 도 동일)

**고아 정리**:
abort 안 된 incomplete uploads 는 _영원히_ 차지 → S3 lifecycle policy 또는 cron.

## 보안 / 검증 가이드

1. **파일명 sanitize** — `..`, `/`, `\`, NUL 제거 → basename 만 사용
2. **MIME 검증** — _클라이언트 Content-Type 신뢰 X_, 매직 바이트 (`python-magic`)
3. **크기 한도** — 누적 검증, nginx `client_max_body_size` 와 일치
4. **AV 스캔** — 사용자 콘텐츠는 ClamAV / VirusTotal API
5. **decompression bomb** — zip/gzip/이미지 _압축률_ 검사 (PIL.Image.verify)
6. **Content-Disposition** — `attachment; filename="..."` 으로 _다운로드 강제_, RFC 5987 한글
7. **`X-Content-Type-Options: nosniff`** — MIME 스니핑 차단
8. **storage 격리** — 사용자 콘텐츠는 _별도 도메인_ (XSS 격리, cookie 격리)

## 안티패턴

1. **`UploadFile.read()` 전체 호출** — 큰 파일 OOM. `read(chunk_bytes)` 루프.
2. **Content-Length 만 보고 한도 검증** — 악성 클라이언트가 거짓말 가능. _누적_ 카운트.
3. **클라이언트 Content-Type 신뢰** — 매직 바이트로 검증.
4. **파일명 그대로 사용** — `../../../etc/passwd` traversal. sanitize 필수.
5. **앱 서버에서 큰 파일 프록시** — 대역폭/메모리 폭발. presigned URL 로 우회.
6. **presigned 만료 너무 길게** (1시간+) — 유출 시 위험. 1~10분.
7. **multipart abort 안 함** — 고아 part 디스크 차지. lifecycle / cron.
8. **`FileResponse` 동적 콘텐츠에** — `StreamingResponse` 가 정답.
9. **스토리지를 _앱 인스턴스 디스크_ 에** — autoscaling 시 데이터 사라짐. S3 / NFS / EFS.
10. **파일 메타데이터를 _파일 이름_ 으로** — `report-2026-01-01-alice.pdf`. DB 에 저장 + 키는 UUID.

## 운영 도구 (참고)

| 영역 | 도구 |
|---|---|
| 객체 스토리지 | AWS S3, GCS, Azure Blob, MinIO (오픈소스 S3 호환), Ceph |
| Python SDK | boto3 / aioboto3 / s3fs (fsspec), google-cloud-storage |
| 이미지 처리 | Pillow, pyvips (대용량), libvips |
| 비디오 | ffmpeg-python, AWS MediaConvert |
| AV | ClamAV (clamd), VirusTotal API |
| MIME 검증 | python-magic, magika (Google ML 기반) |
| 업로드 UI | Uppy.js, react-dropzone, tus.io (resumable upload 표준) |
| 큰 업로드 | tus.io, S3 multipart, GCS resumable upload |

## 직접 해보기 TODO

- [ ] MinIO testcontainers 로 `S3Storage` 구현 — `Storage` Protocol 교체로 검증
- [ ] `python-magic` 으로 _매직 바이트_ MIME 검증 추가
- [ ] 이미지 업로드 시 `Pillow` 로 썸네일 자동 생성
- [ ] `tus.io` resumable upload 프로토콜 구현
- [ ] presigned _다운로드_ URL — 권한 검사 후 발급, 비공개 파일 공유
- [ ] 12 단계 OTel 과 결합 — 업로드 latency / 크기 분포 메트릭
- [ ] CDN 통합 — CloudFront signed URL / Cloudflare R2 signed URL
- [ ] _이미지 서명 변조_ 시도 — `X-Signature` 마지막 글자 바꿔서 403 확인

## 다음 단계

**A10 — GraphQL** (선택). Strawberry 라이브러리, REST vs GraphQL 트레이드오프, N+1 + DataLoader 패턴.
