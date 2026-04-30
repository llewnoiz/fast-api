# A8 — WebSocket / Server-Sent Events / Redis pub/sub fan-out

11 (Redis) + 04 (FastAPI) 의 _실시간_ 확장. 채팅 / 알림 / 라이브 대시보드 / 진행 표시.

## 학습 목표

- **WebSocket** — FastAPI `@app.websocket(...)`, accept / receive_json / send_json
- **ConnectionManager** — room 단위 연결 관리 + broadcast
- **Server-Sent Events** — `text/event-stream` 단방향 스트림, `EventSource` 자동 재연결
- **WS vs SSE 트레이드오프** — 언제 무엇을 쓸지
- **Redis pub/sub fan-out** — _다중 인스턴스_ 간 브로드캐스트

## 디렉토리

```
A8-realtime/
├── pyproject.toml
├── Makefile
├── README.md
├── src/realtime/
│   ├── __init__.py
│   ├── settings.py
│   ├── manager.py             # ConnectionManager (단일 프로세스 broadcast)
│   ├── pubsub.py              # RedisBroker (다중 인스턴스 fan-out)
│   ├── sse.py                 # EventSourceResponse 헬퍼
│   └── main.py                # FastAPI (WS + SSE + HTTP broadcast 라우트)
└── tests/
    ├── conftest.py            # testcontainers Redis (broker / e2e)
    ├── test_manager.py        # 단위 테스트 (Fake WebSocket)
    ├── test_pubsub.py         # 다중 인스턴스 시뮬레이션 (broker 두 개)
    ├── test_websocket_e2e.py  # TestClient.websocket_connect — 채팅 시나리오
    └── test_sse.py            # text/event-stream 응답 검증
```

## 실행

```bash
# 1) Redis 띄우기 (이미 있으면 생략)
make -C ../05-infra-compose up-cache

# 2) 테스트
cd A8-realtime
make all

# 3) 서버
make run
# → http://127.0.0.1:8008/docs
# WebSocket: ws://127.0.0.1:8008/ws/chat/room1?user=alice
# SSE:       curl -N http://127.0.0.1:8008/sse/notifications/alice
```

## WebSocket vs SSE 비교

| 항목 | WebSocket | Server-Sent Events |
|---|---|---|
| **방향** | 양방향 | 서버 → 클라이언트 _단방향_ |
| **프로토콜** | TCP 위 자체 프레이밍 (HTTP Upgrade) | HTTP 그대로 (Content-Type: text/event-stream) |
| **자동 재연결** | ❌ 직접 구현 | ✅ 브라우저 `EventSource` 가 자동 |
| **Last-Event-ID 이어받기** | ❌ | ✅ 브라우저가 헤더 자동 |
| **프록시 / LB 호환** | 일부 설정 필요 (HTTP Upgrade) | HTTP 라 _자연스러움_ |
| **인증** | 연결 시점 토큰 (쿼리 / 헤더) | HTTP 쿠키 / Authorization 그대로 |
| **메시지 형식** | 텍스트 / 바이너리 | UTF-8 텍스트만 |
| **적합 케이스** | 채팅, 게임, 협업 편집 | 알림, 진행 표시, 대시보드 |
| **HTTP/2 multiplex** | ❌ (HTTP/2 위 WS 는 HTTP/3 이후 표준화) | ✅ 같은 connection 으로 N 스트림 |

**선택 휴리스틱**:
- _서버 → 클라이언트만_ 필요? **SSE** ── 인프라 단순함이 크다
- _양방향_ 또는 _저지연_ 필요? **WebSocket**
- 프록시 / 모바일 환경 까다로움 → SSE 우선
- 채팅 / 게임 / 협업 → WS

운영 시: 둘 다 _장기 연결_ 이라 LB / nginx / k8s ingress timeout 늘려야 함 (기본 60초 → 24시간).

## ConnectionManager 패턴

```
client A ──┐
client B ──┼──▶ ConnectionManager.broadcast("room1", {...})
client C ──┘                  │
                              └─▶ 같은 room 의 모든 WS 에 send_json
```

**핵심 동시성 규칙**:
- rooms 변경은 _lock_ 으로 보호
- broadcast 의 send_json 은 lock _밖_ 에서 (느린 send 가 다른 가입 막지 말도록)
- 죽은 연결은 send 실패 시 _자동 정리_

**다국 비교**:
- Spring `SimpMessagingTemplate` (STOMP) — 사용자/세션 자동 라우팅
- Node `socket.io` — `io.to(room).emit(...)` 표준
- ASP.NET SignalR — `Clients.Group(name).Send(...)` 자동 그룹

## Redis Pub/Sub 다중 인스턴스 fan-out

**문제**: 인스턴스 A 의 사용자 1 메시지 → 인스턴스 B 에 연결된 사용자 2 가 못 받음.

```
Instance A                       Instance B                       Instance C
  │ user1 ──msg──▶│                    │                            │
  │  ConnMgr A    │  PUBLISH rt:room1  │                            │
  │       └──────▶├──────▶ Redis ──────┤────────────────────────────┤
  │               │                    │                            │
  │  PSUBSCRIBE   │  PSUBSCRIBE        │  PSUBSCRIBE                │
  │  rt:*         │  rt:*              │  rt:*                      │
  │       ▲       │       ▲            │       ▲                    │
  │  ConnMgr A    │  ConnMgr B         │  ConnMgr C                 │
  │  user1 ◀──┘   │  user2 ◀──┘        │  user3 ◀──┘                │
```

**Redis pub/sub 한계**:
- **at-most-once** ── 구독 안 하던 시점은 누락
- **persistence X** ── Redis 재시작 시 메시지 사라짐
- **scale 한계** ── 단일 Redis 부하

→ 영속 / 순서 / 내구성 필요 시 **Redis Streams** (`XADD`/`XREAD`+consumer group) 또는 **Kafka** (13).

**대안 표**:

| 옵션 | 영속 | 순서 | 적합 |
|---|---|---|---|
| Redis pub/sub | ❌ | 약함 | 가벼운 fan-out |
| Redis Streams | ✅ | 강함 | 가벼운 영속 큐 |
| NATS / JetStream | ✅ | 강함 | 마이크로서비스 메시징 |
| Kafka | ✅ | 강함 | 운영급 표준 |
| Postgres LISTEN/NOTIFY (A6) | ❌ | 약함 | DB 만으로 가벼운 신호 |

## 인증 패턴 — WebSocket

WebSocket 은 _연결 시점_ 에만 인증 가능. 메시지마다 토큰 검증은 _과한 비용_.

```python
@app.websocket("/ws/chat/{room}")
async def ws(websocket: WebSocket, room: str, token: str = Query(...)):
    user = decode_jwt(token)            # 09 단계 패턴
    if user is None:
        await websocket.close(code=1008)  # policy violation
        return
    # ... 정상 흐름
```

**가이드**:
- 토큰은 _쿼리 파라미터_ (`?token=...`) 또는 _첫 메시지_ 로 (`Bearer ...`).
- HTTP 헤더 (Authorization) 도 가능하나 브라우저 `WebSocket` API 가 헤더 못 줌 — 모바일/서버에선 OK.
- _짧은 TTL_ JWT 발급 → 만료 시 클라이언트가 다시 HTTP 로 토큰 갱신 후 재연결.

## SSE 운영 주의사항

1. **Nginx / LB 버퍼링** — `X-Accel-Buffering: no` 또는 `proxy_buffering off` 로 끄기. `EventSourceResponse` 가 자동 헤더 추가.
2. **Idle timeout** — 프록시가 60초 idle 끊음 → `EventSourceResponse` 의 자동 ping 이벤트 활용.
3. **HTTP/1.1 connection limit** — 브라우저당 같은 도메인 SSE _6개_ 한계. 도메인 샤딩 또는 HTTP/2 (무제한).
4. **메모리 누수** — 클라이언트 disconnect 자동 감지 (`EventSourceResponse` 가 generator 종료) 확인.

## 안티패턴

1. **WebSocket 매 메시지에 JWT 검증** — 비용 큼. 연결 시점에 한 번 + _짧은 TTL_.
2. **lazy load 안에서 send_json** — 느린 send 가 lock 잡으면 다른 가입 막힘. broadcast 는 lock 밖.
3. **WS 단일 인스턴스** — 다중 배포 시 _깨짐_. 처음부터 pub/sub 끼워두기.
4. **SSE 응답에 Cache-Control 빼먹음** — 프록시가 캐싱 → 다음 클라이언트가 _옛 데이터_ 받음. `EventSourceResponse` 자동.
5. **SSE 응답을 그냥 텍스트로 작성** — `\n\n` 구분 / `data: ` 접두사 / UTF-8 강제. 라이브러리 (sse-starlette) 권장.
6. **메시지 양 폭주에 대비 안 함** — _per-connection 큐_ + 백프레셔 (queue full → drop 또는 disconnect).
7. **프로덕션에서 ConnectionManager 만 사용** — 인스턴스 1대 한계. autoscaling 안 됨.
8. **`while True: await ws.receive_text()` 무한 루프 + 예외 안 잡음** — disconnect 시 `WebSocketDisconnect` raise. try/finally 로 manager.disconnect.

## 운영 도구 (참고)

| 영역 | 도구 |
|---|---|
| WebSocket 매니저 | socket.io 호환 (Python: `python-socketio`), Centrifugo, Mercure |
| SSE 라이브러리 | sse-starlette (본 모듈), aiohttp-sse |
| 분산 fan-out | Redis pub/sub, Redis Streams, NATS, Kafka, Mercure (SSE 전용 hub) |
| 모니터링 | Prometheus `websocket_connections_total` / `_active_connections` |
| Edge | Cloudflare Workers, Fastly Compute — _구독 fan-out 매니지드_ |

## 직접 해보기 TODO

- [ ] `wscat -c ws://127.0.0.1:8008/ws/chat/room1?user=alice` 로 _두 터미널_ 채팅 확인
- [ ] `curl -N http://127.0.0.1:8008/sse/notifications/alice` + `curl -X POST .../notify/alice -d '{"text":"hi"}'`
- [ ] uvicorn 두 인스턴스 (port 8008, 8009) 띄워 _다른 인스턴스_ 메시지 fan-out 확인
- [ ] WebSocket _하트비트_ 추가 — 30초마다 `ping` / `pong` (네트워크 끊김 빠른 감지)
- [ ] JWT 인증 추가 — 09 단계의 `decode_jwt` 와 결합
- [ ] WebSocket 메시지 _rate limit_ — 11 단계 RateLimiter 와 결합 (사용자별 초당 N개)
- [ ] SSE 의 `Last-Event-ID` 활용 — 재연결 시 _누락된 이벤트만_ 다시 보내기
- [ ] WebSocket 부하 테스트 — `websocat` 또는 `k6/ws` 로 1000 동시 연결

## 다음 단계

**A9 — 파일 업로드 / 다운로드**. multipart / S3 presigned URL / `StreamingResponse` 청크 / 큰 파일 multipart upload.
