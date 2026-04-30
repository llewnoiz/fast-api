# A2 — 부하 테스트 (locust)

본편 끝나고 첫 번째 부록. 06 의 sync vs async 비교를 _진짜 도구_ 로 재현 + 15 tender 골든 패스 부하 측정.

## 학습 목표

- **`locust`** — Python 시나리오 기반 부하 테스트 (분산 가능)
- **부하 형태 5가지** — smoke / load / stress / spike / soak
- **측정 지표** — p50/p95/p99 latency, RPS, 에러율
- 06 의 **sync vs async** 차이를 _진짜 그래프_ 로
- 15 tender 의 **캐시 hit rate** 효과 측정

## 디렉토리

```
A2-load-test/
├── pyproject.toml          # locust
├── Makefile                # make demo-server / load-sync-async / load-tender
├── README.md
└── src/loadtest/
    ├── demo_server.py             # sync/async 미니 서버 (06 응용)
    ├── sync_async_compare.py      # /sync vs /async 시나리오
    └── tender_scenario.py         # 15 tender 골든 패스 시나리오
```

## 다국 언어 비교 — 부하 테스트 도구

| 도구 | 시나리오 언어 | 강점 | 약점 |
|---|---|---|---|
| **locust** | **Python** | 학습 친화, 분산, GUI/headless | RPS 한계 (~1만/머신) |
| **k6** | JavaScript | 빠름, 클라우드 통합, JS 친숙 | Python 외부 |
| **JMeter** | GUI / XML | 풍부, 엔터프라이즈 | 무거움, GUI 의존 |
| **Gatling** | Scala DSL | 매우 빠름, 보고서 좋음 | Scala 진입장벽 |
| **wrk** | C / Lua | 가장 빠름 | 시나리오 작성 빈약 |

학습용으론 **locust** — Python 으로 서버 작성한 우리 환경에 일관성.

## 실행 시나리오

### 1) sync vs async 비교

```bash
# 터미널 1: 미니 서버 (sync + async 두 라우트)
cd A2-load-test
make demo-server
# → http://127.0.0.1:8000/sync, /async

# 터미널 2: locust GUI 모드 — http://localhost:8089 에서 시작
make load-sync-async

# 또는 headless (CI 친화)
make load-sync-async-headless
# → 100명, 20명/초 스폰, 30초 실행
# → 통계 출력 — /sync 가 /async 대비 _압도적으로 느림_
```

기대 결과:
- `/sync`: 평균 ~수 초 latency (FastAPI 스레드 풀 한계)
- `/async`: 평균 ~200~300ms (이벤트 루프 동시 처리)
- 06 의 _인메모리_ 측정 대비 _훨씬 큰_ 차이 (진짜 네트워크 RTT)

### 2) 15 tender 골든 패스

```bash
# 터미널 1: docker compose db + cache
cd ../05-infra-compose && make up

# 터미널 2: tender 마이그레이션 + 서버
cd ../15-mini-project
make migrate
make run

# 터미널 3: _시드 사용자_ 등록 (alice/bob/carol)
# 학습용 — 직접 curl 또는 SQL. 또는 conftest.py 의 register_user 패턴 응용

# 터미널 4: locust
cd ../A2-load-test
make load-tender-headless
```

기대 결과:
- `POST /v2/orders` — DB 트랜잭션 + outbox 기록 (병목: DB)
- `GET /v2/orders/{id}` — 첫 호출 DB, 이후 캐시 (cache hit rate ↑)
- `GET /healthz` — 가장 빠름

## 부하 형태 5가지

| 패턴 | 사용자 수 | 시간 | 목적 |
|---|---|---|---|
| **smoke** | 1~5 | 1분 | 동작 확인 — CI 친화 |
| **load** | 평소 트래픽 | 5~10분 | 정상 부하의 p95 latency |
| **stress** | 점진 증가 → 한계 | 10~30분 | _한계점_ 발견 |
| **spike** | 평소 → _급증_ | 짧게 | 자동 스케일링 / 회로 차단기 검증 |
| **soak** | 낮은 부하 | 수 시간~수 일 | 메모리 누수 / DB 풀 고갈 / 디스크 |

## 측정 지표 — RED + USE

**RED** (Request 관점):
- **R**ate (RPS) — 초당 요청 수
- **E**rrors — 실패율
- **D**uration — p50 / p95 / p99 latency

**USE** (Resource 관점):
- **U**tilization — CPU / 메모리 / 디스크
- **S**aturation — 큐 대기, 스레드 풀 포화
- **E**rrors — OOM, 디스크 풀

12 의 Prometheus + Grafana 가 _RED + USE 모두_ 자동 노출.

## 안티패턴

1. **앱 서버에서 _직접_ locust 실행** — 부하가 앱 자원 잡아먹음. 별도 머신/컨테이너에서.
2. **smoke 없이 바로 stress** — 정상 동작도 확인 안 됨. 항상 smoke → load → stress.
3. **사용자 수만 보고 `RPS = users`** 가정 — wait_time 에 따라 다름. 측정으로 확인.
4. **단일 라우트만 타격** — 현실은 여러 라우트 _섞여_ 옴. `@task(weight)` 로 가중치.
5. **`time.sleep` 으로 대기** — locust 가 그 시간만큼 멈춤. `wait_time = between(...)` 사용.
6. **운영 DB 에 부하** — 학습엔 OK 지만 운영은 _복제본_ 또는 _격리 환경_.
7. **JWT 토큰 만료 무시** — 긴 부하 테스트에선 `on_start` 이후 갱신 로직 필요.
8. **로컬 머신 = 운영 추정** — 네트워크 / CPU / 메모리가 다름. 운영급 머신에서 측정.

## 보고서 / 그래프 — 운영급

locust GUI:
- 실시간 RPS / latency / 실패율
- HTML 보고서 export

운영 통합:
- locust → Prometheus → Grafana (12 + 부하 대시보드)
- locust 클러스터 (master + workers) — 한 머신 한계 돌파

## 직접 해보기 TODO

- [ ] sync vs async 부하를 1분 돌려 _스크린샷_ 으로 차이 기록
- [ ] tender 시나리오로 캐시 효과 측정 — `GET /v2/orders/{id}` p95 가 _시간 지나며 줄어드는지_
- [ ] 11 의 rate limit 동작 — 사용자 수 늘려서 429 발생 비율 확인
- [ ] **stress 패턴**: 5분 동안 사용자 10 → 500 까지 점진 증가, 한계점 측정
- [ ] **spike 패턴**: 평소 100명 운영 중 _10초간 1000명_ 폭증
- [ ] locust master + 2 worker — 분산 모드 (`--master`, `--worker`)
- [ ] k6 로 같은 시나리오 작성해 비교

## 다음 단계

**A3 — CI/CD 파이프라인** (GitHub Actions). 본편 + A2 의 _모든 단계_ 에 자동 빌드/테스트/배포.
