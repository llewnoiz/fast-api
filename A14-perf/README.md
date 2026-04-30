# A14 — 성능 / 프로파일링 (마지막 트랙 🎓)

CPU / 메모리 / async / 알고리즘 — _측정_ 으로 최적화하는 학습. **"measure, don't assume."**

## 학습 목표

- **cProfile** — 함수 단위 누적 시간 + 호출 수 (deterministic)
- **tracemalloc** — 메모리 추적 + snapshot diff + 누수 탐지
- **async 성능 함정** — blocking 호출 / 직렬 await / 누락된 await / executor
- **알고리즘 복잡도** — O(n²) vs O(n) _실제 측정_ (직관 X)
- **캐시 효과** — `@cache` / `cached_property` 가 _언제 이득_ 인지
- **워커 모델** — uvicorn vs gunicorn, HTTP/2, 워커 수 결정
- **외부 도구** — py-spy / memray / pyinstrument / scalene / line_profiler

## 디렉토리

```
A14-perf/
├── pyproject.toml
├── Makefile
├── README.md
├── src/perfdeep/
│   ├── __init__.py
│   ├── bench_utils.py         # bench() + p50/p95/p99 통계
│   ├── cprofile_demo.py       # cProfile + pstats + fib_naive vs iterative
│   ├── tracemalloc_demo.py    # 메모리 측정 + leaky vs clean 시뮬
│   ├── async_pitfalls.py      # 5가지 함정 + executor + slow callback 탐지
│   ├── algorithm_complexity.py # 검색/중복/카운트/누적 ── 복잡도 비교
│   ├── cache_bench.py         # @cache 효과 + cached_property
│   ├── workers.py             # gunicorn / uvicorn 운영 가이드
│   └── external_tools.py      # py-spy / memray / pyinstrument 사용 패턴
└── tests/
    ├── test_bench_utils.py
    ├── test_cprofile.py
    ├── test_tracemalloc.py
    ├── test_async_pitfalls.py
    ├── test_algorithm_complexity.py
    └── test_cache_bench.py
```

## bench 헬퍼 — 단순 측정

```python
from perfdeep.bench_utils import bench, faster

slow_result = bench("naive", lambda: slow_fn(), iterations=100, warmup=5)
fast_result = bench("optimized", lambda: fast_fn(), iterations=100, warmup=5)

print(f"slow p50: {slow_result.p50*1000:.2f}ms")
print(f"fast p50: {fast_result.p50*1000:.2f}ms")
print(f"speedup: {faster(fast_result, slow_result):.1f}x")
```

운영급은 **pytest-benchmark** (CI 통합) / **pyperf** (가장 정확).

## cProfile 흐름

```python
from perfdeep.cprofile_demo import profile_call

result, stats = profile_call(lambda: my_function())
print(stats)   # 누적 시간 _상위 20 함수_
```

**언제 사용?**
- _어떤 함수_ 가 느린지 모를 때 — 광범위 → cProfile
- 그 다음 좁히면 → **line_profiler** (라인 단위)

**vs sampling profiler**:
- cProfile: deterministic, 정확, 10~50x 오버헤드
- **py-spy / pyinstrument**: sampling, 거의 0 오버헤드, 짧은 함수 누락 가능

## tracemalloc — 메모리

```python
from perfdeep.tracemalloc_demo import measure_memory

result, report = measure_memory(my_function)
print(f"current={report.current_bytes}")
print(f"peak={report.peak_bytes}")
for line, size in report.top_lines:
    print(f"{size:>10} bytes at {line}")
```

**누수 인시던트**:
1. RSS 그래프로 _증가 추세_ 발견 (Prometheus `container_memory_rss`)
2. 의심 시간대에 `tracemalloc` snapshot _두 번_ (5분 간격)
3. snapshot diff 로 _증가한 위치_ 추적
4. heap 분석 ── 같은 객체 누적인지, 라인이 매번 새로 만드는지

**vs memray**:
- tracemalloc: 내장, 가벼움, snapshot diff
- **memray** (Bloomberg): flame graph, native 메모리 (numpy / Pillow), 강력

## async 함정 5종

### 1. blocking 호출
```python
async def bad():
    time.sleep(1)         # ❌ 이벤트 루프 _전체_ 멈춤
async def good():
    await asyncio.sleep(1)  # ✅ yield → 다른 task 진행
```

### 2. 순차 await
```python
# ❌ 직렬 — 총시간 = sum(각 시간)
for x in xs:
    result = await fetch(x)
# ✅ 병렬 — 총시간 = max(각 시간)
results = await asyncio.gather(*[fetch(x) for x in xs])
```

### 3. CPU bound 을 async 로
```python
async def cpu_bad():
    return sum(i*i for i in range(10**7))   # async 의 _이점 X_

async def cpu_good():
    return await asyncio.to_thread(cpu_func)   # 스레드 풀 (GIL — I/O 만 진짜 병렬)
    # 또는 ProcessPoolExecutor (진짜 병렬, IPC 비용)
```

### 4. 누락된 await
```python
async def fail():
    raise RuntimeError("...")

t = asyncio.create_task(fail())   # await 안 하면 _조용히_ 실패
# 항상 `await t` 또는 `gather` 또는 `TaskGroup`
```

### 5. 탐지: slow_callback_duration
```python
loop = asyncio.get_event_loop()
loop.slow_callback_duration = 0.1   # 100ms 이상 동기 콜백 → 로그 경고
```

## 알고리즘 복잡도 — 측정으로 차이 체감

| 작업 | naive | 최적 |
|---|---|---|
| 검색 (정렬됨) | O(n) linear | **O(log n) binary** |
| 중복 검사 | O(n²) 모든 쌍 | **O(n) set** |
| 빈도 카운트 | `if k in d` 두 lookup | `d.get(k, 0) + 1` |
| 누적 합 | O(n²) 매번 sum() | **O(n) running total** |
| 문자열 연결 | `s += w` (O(n²)) | **`"".join()` (O(n))** |

**우리 테스트가 _실제로_ 검증** — `make test` 가 5x ~ 100x 차이 확인.

## 캐시 효과

| 함수 | 캐시 효과 |
|---|---|
| `fib(n)` 재귀 | **O(2^n) → O(n)** ← 엄청남 |
| `add(a, b)` | _느려짐_ — lookup 비용이 더 큼 |
| 인스턴스 메서드 + `@cache` | **메모리 누수** — self 가 키 → 인스턴스 영원 |
| 인스턴스 메서드 + `@cached_property` | _인스턴스 단위 캐시_ ── 인스턴스 죽으면 같이 죽음 |

원칙: **"measure, don't assume."** 짧은 함수 캐시는 _느려질 수도_.

## 워커 모델 — 운영

```bash
# Production 권장
gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --workers $((2 * $(nproc) + 1)) \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30
```

**워커 수**:
- I/O bound (DB / 외부 API) → `2 × CPU + 1`
- CPU bound → `CPU`
- 메모리 제약 → `메모리 / 워커 메모리`

**`--max-requests`**: 워커가 N 요청 처리 후 _재시작_ ── 메모리 누수 _완화_.

**HTTP/2 / HTTP/3**: uvicorn / gunicorn _미지원_ ── Nginx / Envoy / CloudFront 가 종단처리.

**hot reload (`--reload`) 운영 절대 금지**: 모듈 import 시점 코드 매번 실행, DB 풀 leak.

## 외부 도구 (`make` 시연 X — pip install 후 CLI)

| 도구 | 강점 |
|---|---|
| **py-spy** | 운영 _live_ 프로세스, 거의 0 오버헤드, ptrace 기반 |
| **memray** | flame graph, native 메모리, Bloomberg 작품 |
| **pyinstrument** | call tree sampling, async 친화, 짧은 보고서 |
| **scalene** | CPU + 메모리 + GPU + AI 최적화 제안 |
| **line_profiler** | 라인 단위 (cProfile 다음 단계) |
| **pyperf** | 가장 정확한 마이크로 벤치 (warmup, GC 제어) |

## CPU bound 가속 (핫스팟 발견 시 우선순위)

1. **NumPy / SciPy** — 벡터 연산 (수십 배)
2. **Numba `@njit`** — JIT 컴파일 (한 줄 추가)
3. **Cython** — C 컴파일 (모든 코드)
4. **PyO3 (Rust)** — 가장 모던 (cryptography / pydantic-core / polars 가 사용)

## 안티패턴

1. **측정 없이 "이게 느려" 판단** — _intuition_ 거의 항상 틀림
2. **마이크로 벤치만 보고 운영 결정** — 워밍업 / 캐시 / GC 의 영향 전혀 안 봄
3. **모든 함수에 `@cache`** — 짧은 함수는 _느려짐_, 인스턴스 메서드는 _누수_
4. **`time.sleep` 을 async 안에** — 이벤트 루프 멈춤
5. **CPU bound 에 더 많은 async worker** — GIL 때문에 효과 없음
6. **메모리 그래프만 보고 누수 단정** — 보통 _로그 누적_, _캐시 늘어남_, _증가 추세 vs steady state_ 구분
7. **`--reload` 운영 사용** — DB 커넥션 / Redis 풀 누수
8. **pickle / json 직렬화 비용 무시** — 큰 데이터 IPC 시 _직렬화_ 가 진짜 병목
9. **로그를 운영 hot path 에 INFO** — 디스크 / 네트워크 IO + 직렬화 비용
10. **GC 튜닝 전에 알고리즘 검토 안 함** — `gc.set_threshold` 전에 _할당 줄이는 것_ 우선

## 직접 해보기 TODO

- [ ] `py-spy top --pid <uvicorn-pid>` ── 15 단계의 tender 띄우고 부하 → live CPU 분포
- [ ] `memray run -o m.bin` 후 `memray flamegraph m.bin` ── tender 의 메모리 hot path
- [ ] cProfile 로 _15 단계 tender_ 의 `place_order` 분석 → 가장 느린 곳 찾기
- [ ] `asyncio.get_event_loop().slow_callback_duration = 0.1` 켜고 운영 흉내 → 어떤 코드가 _100ms 이상_ 동기 차단인지
- [ ] **Numba @njit** 로 fib_iterative 재작성 → bench 비교 (Python 대비 _수십 배_)
- [ ] **PyO3** 로 Rust 모듈 (예: 정렬) — 같은 문제 해결 후 bench 비교
- [ ] gunicorn `--max-requests` 효과 — 메모리 _누수 함수_ 깔고 워커 _주기적 재시작_ 효과 측정
- [ ] **pyperf** 로 본 모듈의 bench 결과 vs pyperf 결과 — 정확도 차이 확인

## 🎓 졸업 — 부록 트랙 14 _완주_

본 트랙으로 **A2 ~ A14 모든 부록 + 본편 15단계** 완성.

다국 비교 / 운영 함정 / 학습 모듈을 _하나의 모노레포_ 로 정리 — 다음 프로젝트의 _참조 자료_ 로.
