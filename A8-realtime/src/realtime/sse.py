"""Server-Sent Events 헬퍼.

SSE 는 _HTTP 위_ 의 _단방향_ (서버 → 클라이언트) 스트리밍.
표준: WHATWG `text/event-stream` 미디어 타입.

**WS vs SSE 비교**:

| | WebSocket | Server-Sent Events |
|---|---|---|
| 방향 | 양방향 | 단방향 (서버 → 클라이언트) |
| 프로토콜 | TCP 위 자체 프레이밍 | HTTP 그대로 |
| 자동 재연결 | ❌ 직접 | ✅ 브라우저 `EventSource` 자동 |
| 프록시 호환 | 일부 프록시 / LB 설정 필요 | HTTP 라 _자연스러움_ |
| 인증 | _연결 시점_ 토큰 (쿼리/헤더) | HTTP 쿠키 / Authorization 그대로 |
| 메시지 형식 | 텍스트 / 바이너리 | UTF-8 텍스트만 |
| 적합 케이스 | 채팅, 게임, 협업 | 알림, 대시보드, 진행 표시 |

**브라우저 측**:
```js
const es = new EventSource("/sse/notifications");
es.addEventListener("message", e => console.log(JSON.parse(e.data)));
es.addEventListener("custom", e => ...);  // 이벤트 이름 지정 시
```

**다국 비교**:
- Node `res.setHeader('Content-Type', 'text/event-stream')` 로 직접 작성, `data: ...\n\n`
- Spring `SseEmitter` — 동기 thread-per-client 라 _수천 개_ 한계 (운영은 reactor 또는 reactive)
- ASP.NET 같은 표준 라이브러리 X — 직접 컨트롤러 구현
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from sse_starlette.sse import EventSourceResponse, ServerSentEvent


async def event_stream(queue: asyncio.Queue[dict[str, str | int]]) -> AsyncIterator[ServerSentEvent]:
    """Queue 에 들어오는 항목을 SSE 이벤트로 변환. 하트비트는 `EventSourceResponse` 가 자동.

    payload 형식 가이드:
        {"event": "notify", "data": "...", "id": "123", "retry": 3000}
        - event: 클라이언트 측 `addEventListener("notify", ...)` 와 매칭
        - id: 재연결 시 `Last-Event-ID` 헤더로 _이어받기_ (브라우저 자동)
        - retry: 재연결 지연 (ms)
    """
    while True:
        item = await queue.get()
        # ServerSentEvent 가 `data: ...\nevent: ...\nid: ...\n\n` 직렬화
        yield ServerSentEvent(
            data=str(item.get("data", "")),
            event=str(item["event"]) if "event" in item else None,
            id=str(item["id"]) if "id" in item else None,
            retry=int(item["retry"]) if "retry" in item else None,
        )


def make_sse_response(queue: asyncio.Queue[dict[str, str | int]]) -> EventSourceResponse:
    """FastAPI 라우트에서 `return make_sse_response(queue)`.

    `EventSourceResponse` 가 자동 처리:
        - Content-Type: text/event-stream
        - Cache-Control: no-cache + X-Accel-Buffering: no (nginx 버퍼링 방지)
        - 주기적 ping (`event: ping`) 으로 _idle 연결_ 유지 (LB / 프록시 timeout 회피)
        - 클라이언트 disconnect 자동 감지 → generator 종료
    """
    return EventSourceResponse(event_stream(queue))
