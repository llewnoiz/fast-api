"""t02 — httpx: requests 의 후계자 + async 지원.

비교:
    Node/JS:    fetch (브라우저/Node 18+), axios
    TypeScript: fetch + 자체 wrapper, ky, axios
    Kotlin:     ktor-client, OkHttp + Coroutines
    Java:       Java 11 HttpClient (sync/async), Spring WebClient
    PHP:        Guzzle
    Go:         net/http

httpx 의 강점:
    - requests 와 _거의 같은 API_ → 마이그레이션 쉬움
    - **sync/async 둘 다** (axios / ktor-client 와 같은 자리)
    - HTTP/2, connection pooling, mock transport 내장
    - FastAPI 가 기본으로 추천하는 클라이언트

이 모듈에서:
    1. 동기 GET — 가장 단순
    2. 비동기 GET — async/await
    3. asyncio.gather 로 _병렬_ 호출 (Kotlin coroutineScope { async {} } 자리)
    4. mock transport — 테스트에서 _진짜_ 외부 호출 안 하기
    5. AsyncClient 재사용 (12 단계 떡밥)
"""

from __future__ import annotations

import asyncio

import httpx

# ============================================================================
# 1) 동기 — requests 와 동일한 감각
# ============================================================================
#
# requests:    r = requests.get("https://api.example.com")
# httpx (sync):r = httpx.get("https://api.example.com")
# axios:       const r = await axios.get("https://api.example.com")
# ============================================================================


def fetch_sync(url: str) -> dict[str, object]:
    """단발 동기 호출. 짧은 스크립트에 OK, 서버 코드엔 _async 권장_."""
    response = httpx.get(url, timeout=5.0)
    response.raise_for_status()       # 4xx/5xx 면 예외 — Spring `WebClient.onStatus` 자리
    return response.json()


# ============================================================================
# 2) 비동기 — Kotlin suspend fun + ktor-client 자리
# ============================================================================


async def fetch_async(url: str) -> dict[str, object]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


# ============================================================================
# 3) 병렬 호출 — asyncio.gather = Kotlin coroutineScope { listOf(async {...}) }
# ============================================================================
#
# Kotlin:
#   val results = coroutineScope {
#       listOf(async { fetchA() }, async { fetchB() }).awaitAll()
#   }
#
# Python:
#   async with httpx.AsyncClient() as c:
#       a, b = await asyncio.gather(c.get("/a"), c.get("/b"))
#
# 동시에 _시작_ 하고 둘 다 끝날 때까지 _기다림_. 순차 호출 대비 RTT 만큼 절약.
# ============================================================================


async def fetch_many(urls: list[str]) -> list[dict[str, object]]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        # gather: 모든 task 를 _동시에_ 실행. 하나라도 실패하면 전체 실패 (return_exceptions=True 로 변경 가능)
        responses = await asyncio.gather(*(client.get(u) for u in urls))
        return [r.json() for r in responses]


# ============================================================================
# 4) Mock transport — 테스트에서 _진짜_ 외부 호출 X
# ============================================================================
#
# axios 의 axios-mock-adapter, ktor-client 의 MockEngine 자리.
# 테스트는 격리되고 빠르고 결정적이어야 함 — 진짜 네트워크는 통합 테스트에서만.
# ============================================================================


def make_mock_client() -> httpx.Client:
    """가짜 응답을 돌려주는 sync 클라이언트.

    아래 테스트(test_tours.py) 에서 사용.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/users/1":
            return httpx.Response(200, json={"id": 1, "name": "Alice"})
        if request.url.path == "/users/999":
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json={"echo": str(request.url)})

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport, base_url="https://mock")


def make_mock_async_client() -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"path": request.url.path})

    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, base_url="https://mock")


# ============================================================================
# 5) AsyncClient 재사용 — 12 단계의 핵심 패턴
# ============================================================================
#
# 잘못된 패턴: 매 요청마다 AsyncClient() 새로 만들기 → 커넥션 풀 못 씀 → 느림.
# 올바른 패턴: 앱 lifespan 동안 _하나_ 만들고 의존성 주입으로 공유.
#
# 12 단계 (서버간 통신 + 관측가능성) 에서 본격적으로 다룸.
# ============================================================================


def main() -> None:
    print("=== 1) Mock transport (sync) ===")
    with make_mock_client() as client:
        r = client.get("/users/1")
        print("200:", r.status_code, r.json())
        r = client.get("/users/999")
        print("404:", r.status_code, r.json())

    print("\n=== 2) Mock transport (async) ===")

    async def _async_demo() -> None:
        async with make_mock_async_client() as client:
            # asyncio.gather 로 동시 호출
            r1, r2, r3 = await asyncio.gather(
                client.get("/a"),
                client.get("/b"),
                client.get("/c"),
            )
            print("동시 호출 결과:", [r.json() for r in (r1, r2, r3)])

    asyncio.run(_async_demo())


if __name__ == "__main__":
    main()
