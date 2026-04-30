"""워커 / 프로세스 모델 노트 (코드 X — 운영 가이드).

**uvicorn vs gunicorn**:

| 도구 | 역할 | 특징 |
|---|---|---|
| **uvicorn** | ASGI 서버 (이벤트 루프) | 단일 프로세스 / 멀티 워커 (`--workers N`) |
| **gunicorn** | 프로세스 매니저 | uvicorn 워커 _관리_ (`-k uvicorn.workers.UvicornWorker`) |
| **hypercorn** | ASGI 서버 (HTTP/2 + HTTP/3) | uvicorn 대안, async only |

**전형적 운영 셋업**:
```bash
# 옵션 A: gunicorn + uvicorn worker (production 권장)
gunicorn app.main:app \\
    -k uvicorn.workers.UvicornWorker \\
    --workers $((2 * $(nproc) + 1)) \\
    --max-requests 1000 \\
    --max-requests-jitter 50 \\
    --timeout 30

# 옵션 B: uvicorn 단독 (간단한 경우)
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

**워커 수**:
    - I/O bound (DB / 외부 API 위주) → _2 × CPU + 1_ (gunicorn 기본)
    - CPU bound → _CPU 수_
    - 메모리 제약 → _메모리 / 워커 메모리_

**`--max-requests`**:
    워커가 N 요청 처리 후 _재시작_ ── 메모리 누수 _완화_ (영구 해결 X).
    `jitter` 로 _동시 재시작 방지_.

**HTTP/2 / HTTP/3**:
    - **HTTP/2** ── 단일 connection 으로 multiplex. SSE 같은 _장기 연결_ 친화.
    - **HTTP/3** (QUIC) ── UDP 위, 연결 ID, head-of-line blocking 해결.
    - uvicorn / gunicorn 는 _HTTP/2 미지원_ ── 보통 _Nginx / Envoy / CloudFront_ 가 종단처리.

**`--reload` / `--workers` 동시 사용 X**:
    개발은 `--reload` (단일 프로세스). 운영은 `--workers`.

**hot reload 함정**:
    - import time side effect (모듈 import 시점 코드) 가 매번 실행
    - DB 커넥션 / Redis 풀 leak 가능
    - 프로덕션은 _hot reload 절대 금지_

**그라스풀 셧다운**:
    SIGTERM → 워커가 _진행 중 요청 끝까지_ → SIGKILL.
    K8s `terminationGracePeriodSeconds` 와 `--graceful-timeout` 일치 시켜야.

**process model 비교**:
    Java: Tomcat / Jetty 워커 스레드 (스레드당 한 요청)
    Go: 한 프로세스 + goroutine (하나가 N 요청)
    Rust: 한 프로세스 + tokio task (Go 와 비슷)
    Node: 단일 이벤트 루프 + cluster (uvicorn 과 가까움)

**측정 도구**:
    - `gunicorn --statsd-host` ── statsd 메트릭
    - `prometheus-fastapi-instrumentator` (12 단계)
    - `py-spy top --pid <gunicorn-master>` ── 워커별 CPU 사용 _live_
"""
