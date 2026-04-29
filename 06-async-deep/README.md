# 06 — async 심화

지금까지 _async 키워드를 쓰기만_ 했다면, 06 에서 _내부 동작_ 까지. 04 의 `lifespan`, 03 의 `httpx.AsyncClient`, 그리고 06 이후의 DB / Redis / Kafka 클라이언트가 모두 async 라 — 이 단계가 _기반_ 이다.

## 학습 목표

- 이벤트 루프 모델 — Python ≈ Node, ≠ Go/Loom
- `asyncio.run` / `gather` / `TaskGroup` (3.11+)
- **가장 큰 함정**: async 안에서 sync I/O 호출 (`time.sleep`, `requests.get`)
- 어쩔 수 없는 sync 함수: `asyncio.to_thread`
- CPU bound: `ProcessPoolExecutor`
- 타임아웃 + 취소 (`asyncio.timeout`, `Task.cancel`)
- async generator + async for
- **FastAPI sync 라우트 vs async 라우트** — 부하 비교 데모

## 실행

```bash
cd .. && uv sync && cd 06-async-deep

make run                              # 7개 데모 순차
make demo M=t03_antipattern           # 하나만
make test                             # pytest
make all                              # ruff + mypy + pytest
```

## 비교 — 모델 자체부터 다름

| 언어/플랫폼 | 모델 | 한 줄 |
|---|---|---|
| **Python asyncio** | 단일 스레드 + 이벤트 루프 | I/O 시점에 코루틴 전환 |
| **Node** | _거의 동일_ — libuv 이벤트 루프 | Python asyncio 와 가장 비슷 |
| **Kotlin coroutines** | 디스패처 + 구조적 동시성 | 가장 _체계화_ 된 모델 |
| **Java Project Loom (Virtual Threads)** | 가벼운 OS 스레드 | 코드는 sync 처럼, 런타임이 알아서 |
| **Go goroutine** | M:N 스케줄러, 채널 | 다중 OS 스레드, 명시적 채널 |

**Python 은 Node 와 가장 가까움**. _단일 스레드_ 에 이벤트 루프 하나. 그래서 _블로킹_ 호출 한 개가 _전체 처리량_ 을 망가뜨림.

## 7개 데모 요약

| # | 모듈 | 한 줄 |
|---|---|---|
| t01 | `t01_event_loop` | 코루틴 객체 / await / `asyncio.run` |
| t02 | `t02_concurrent` | `gather` 동시 / 순차 / `TaskGroup` (3.11+) |
| t03 | `t03_antipattern` | **sync I/O 가 async 를 _죽이는_ 시각적 증명** |
| t04 | `t04_executor` | `asyncio.to_thread` (sync I/O), `ProcessPoolExecutor` (CPU) |
| t05 | `t05_timeout_cancel` | `asyncio.timeout` (3.11+), `Task.cancel`, ExceptionGroup |
| t06 | `t06_async_iter` | async generator + async for + 변환 파이프라인 |
| t07 | `t07_fastapi_loadcompare` | **FastAPI sync vs async 라우트 — 동시 50개 요청 부하 비교** |

## 핵심 개념

### 1) 코루틴 객체 ≠ 호출 결과

```python
async def hello() -> str: ...

x = hello()       # ← _아직 실행 안 됨_. 코루틴 객체.
y = await hello() # ← 실행하고 결과 받음.
```

**Node async 함수와 비슷하지만 한 가지 차이**: Node 는 async 함수 호출 = Promise (즉시 시작), Python 은 _await 또는 task 생성_ 을 해야 _시작_. 더 _명시적_.

### 2) gather vs TaskGroup

```python
# gather — 옛날부터 있음, 가장 많이 봄
results = await asyncio.gather(coro_a, coro_b, coro_c)

# TaskGroup — 3.11+, _구조적 동시성_ (Kotlin coroutineScope 와 동일)
async with asyncio.TaskGroup() as tg:
    a = tg.create_task(coro_a)
    b = tg.create_task(coro_b)
# 블록 끝나면 모든 task 끝났음을 _보장_, 하나 실패하면 형제들 자동 취소
```

| 도구 | 언제 |
|---|---|
| `gather` | 단순한 동시 실행, 옛 코드 호환 |
| **`TaskGroup`** | 3.11+ 이면 무조건 이쪽. 안전·구조적 |
| `gather(return_exceptions=True)` | 일부 실패 OK 한 _플레이크 허용_ 호출 |

### 3) **가장 큰 함정** — sync I/O 가 async 를 죽인다

```python
# ❌ 안티패턴
async def bad():
    time.sleep(1)            # 이벤트 루프 1초 _완전 멈춤_
    requests.get(url)        # 같은 문제 — 같은 스레드 점유

# ✅ 정답
async def good():
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as c:
        await c.get(url)
```

**왜?** Python asyncio 는 단일 스레드. `time.sleep(1)` 은 그 _단일 스레드_ 를 1초간 점유 → 이벤트 루프가 _다른 어떤 코루틴도_ 못 굴림.

t03 데모로 _직접 측정_:
- 전부 async → 200ms (gather 동시)
- 전부 sync → 600ms (실질 순차)
- 섞기 → 그 이상 (한 sync 가 다른 모든 async 막음)

### 4) sync 라이브러리만 있을 때 — `asyncio.to_thread`

```python
import asyncio

# 옛 sync 라이브러리만 있는 상황
def slow_sync_call(): ...

async def safe_caller():
    result = await asyncio.to_thread(slow_sync_call)   # 스레드 풀에서 실행
    return result
```

- **Kotlin** `withContext(Dispatchers.IO) { ... }` 와 같은 자리
- **GIL 주의**: I/O 바운드는 OK, CPU 바운드는 _진짜 병렬 안 됨_ → ProcessPool 사용

### 5) FastAPI sync 라우트 vs async 라우트

```python
@app.get("/sync")
def sync_route():           # sync — FastAPI 가 _스레드 풀_ 에서 실행
    time.sleep(0.2)

@app.get("/async")
async def async_route():    # async — 이벤트 루프에서 직접
    await asyncio.sleep(0.2)
```

t07 부하 비교 (동시 50개):

| 라우트 | 예상 시간 | 이유 |
|---|---|---|
| `/sync` | 수 초 | FastAPI 스레드 풀 _기본 한정_ |
| `/async` | ≈ 200ms | 한 스레드의 이벤트 루프가 50개 await 를 동시에 |

**규칙**: I/O 의존이면 _무조건 async + async 라이브러리_. CPU 의존이면 sync 로 두고 워커 늘리거나 async + ProcessPool.

### 6) 타임아웃 / 취소 — 03.11+ 의 `asyncio.timeout`

```python
async with asyncio.timeout(0.5):
    await some_slow_call()
# 0.5초 넘으면 TimeoutError + 자동 취소
```

비교:
- Kotlin: `withTimeout(500) { ... }`
- Node: `AbortSignal.timeout(500)`
- Go: `context.WithTimeout(...)`

**취소는 `CancelledError` 예외로** 코루틴에 도착 → `try/finally` 로 정리 가능.

## 안티패턴 8가지

1. **async 함수 안에서 `time.sleep`/`requests.get`** — 이벤트 루프 멈춤. 항상 async 라이브러리.
2. **CPU bound 를 그냥 async 함수로** — GIL 때문에 병렬 X, 다른 코루틴도 멈춤. `ProcessPool` 로.
3. **`gather` 결과 안 받고 _그냥_ 호출** — 코루틴 객체만 만들고 안 await → "coroutine never awaited" 경고.
4. **task 만들고 안 기다리기** — `asyncio.create_task(coro)` 후 await 안 하면 가비지 컬렉션 경고. `TaskGroup` 권장.
5. **`asyncio.run` 을 _라이브러리 코드_ 안에서 호출** — 이미 루프 도는 곳에선 `RuntimeError`. run 은 _진입점_ 한 번만.
6. **취소 후 await 안 함** — `task.cancel()` 만 하고 끝내면 정리 미완료. 항상 `await task` 또는 `with suppress`.
7. **`asyncio.gather` 의 `return_exceptions=False` 인데 일부 실패 → 의도치 않게 다른 task 취소** — 의도된 동작이지만 모르고 쓰면 함정.
8. **운영에서 `asyncio.run` 을 매 요청마다** — 새 이벤트 루프 만드는 비용. FastAPI/uvicorn 이 알아서.

## 직접 해보기 TODO

- [ ] `t02` 의 `with_gather` 결과 순서가 _제출 순서_ 와 같은지 확인 (가장 늦게 끝난 것도 같은 인덱스에)
- [ ] `t03` 의 `mixed()` 가 _왜_ 600ms 가까이 걸리는지 print 로 시각화 (sync task 가 async 들 사이에 끼어들었는지)
- [ ] `t04` 의 `crunch_with_processes` 워크로드를 1개로 줄여서 실행 시간 측정 → 4개일 때와 비교
- [ ] `t05` 의 `auto_cancel_in_taskgroup` 에서 `except*` 대신 `except Exception` 으로 바꿔보고 결과 차이
- [ ] `t06` 의 `even_squares` 에 `async for` 가 진행되는 동안 _다른 코루틴이 실행되는지_ 다른 task 추가해서 시각화
- [ ] `t07` 의 부하 비교를 동시성 100, 500 으로 늘려서 sync 라우트의 한계가 어디서 보이는지

## 다음 단계

**07 — 요청·응답 모델 + 공통 에러 + API 버전 관리**. 04 의 미니 라우트들을 _실무 구조_ 로. 응답 envelope, 에러 코드 표준화, `/v1`·`/v2` 라우터 분리.
