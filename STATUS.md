# 학습 진행 상황 (이어 작업용 노트)

> **내일 시작할 때**: 새 Claude 세션에서 이 파일을 보여주거나 "STATUS.md 보고 03단계 진행해줘" 라고 말하면 됨.

마지막 작업: 2026-04-27 — 02 단계 완료, 03 단계 진입 직전

## 진행 체크

| # | 단계 | 상태 |
|---|---|---|
| 01 | python-basics | ✅ 완료 (스크립트 + 컴프리헨션 build-up + 구조 분해/결합 모듈) |
| 02 | package-structure | ✅ 완료 (greeter 패키지 + CLI entry point + pre-commit) |
| **03** | **libraries-tour** | **⏭️ 다음에 시작** |
| 04~15 | (이후 단계) | ⚪ 대기 |

전체 커리큘럼: [`/Users/hyunmin.song/.claude/plans/fast-api-python-tender-key.md`](file:///Users/hyunmin.song/.claude/plans/fast-api-python-tender-key.md)

## 1단계 완료 — `01-python-basics/`

기본 학습:
- `s01_types.py` — 타입 힌트, Optional, 컬렉션 힌트
- `s02_collections.py` — list/tuple/dict/set + **컴프리헨션 STEP 1~7 build-up** (사용자 질문에 따라 확장)
- `s03_control_flow.py` — if/for/while-else/match(3.10+)/예외
- `s04_functions.py` — 가변·키워드 인자, PEP 695 데코레이터
- `s05_classes.py` — 클래스, dataclass, Enum, Protocol(duck typing)
- `s06_modules.py` — 모듈/패키지/import (사용자가 try/except 폴백을 단순화함)
- `s07_unpacking.py` — **구조 분해/결합 STEP 1~7** (사용자 질문에 따라 확장, Node/JS 비교 중심)
- `tests/test_basics.py` — 60개 pytest 통과

세션 중 **사용자가 추가 설명을 요구했던 주제** (다시 헷갈리면 README 참고):
- 컴프리헨션 — `if` 의 두 가지 위치 (filter vs 표현식 자리 삼항)
- `zip` — 리액티브 X, 그냥 동기 컬렉션 짝짓기
- `while/else` — `while` 에 붙은 else (break 없이 끝났을 때만 실행)
- `match` 의 `case ... if ...` (guard) + `case _:` (와일드카드)
- 구조 분해 / 결합 — Node `const {a, b} = obj` 의 부재 + 4가지 대안
- `try/except/else/finally` 4단 + `raise X from Y` 예외 체인
- `pass` — 빈 블록을 표현하는 키워드 (Python 의 `{}` 자리)

## 2단계 완료 — `02-package-structure/`

`greeter` 미니 라이브러리 + CLI 로 패키지 구조 학습:
- src layout (`src/greeter/`)
- `pyproject.toml` PEP 621 + `[project.scripts]` 콘솔 스크립트 등록
- 절대 vs 상대 import
- 순환 import 회피 3가지 (`circular_demo.py` 주석)
- ruff / mypy / pre-commit 도입 — 루트 `.pre-commit-config.yaml`

핵심 함정 (디버깅함): **워크스페이스 멤버는 자동 install 안 됨**.
루트 `pyproject.toml` 의 `[project.dependencies]` 에 멤버 이름 추가 + `[tool.uv.sources]` 로 `{ workspace = true }` 명시 필요.

## 환경 / 도구 (확정된 선택)

- Python 3.12 (uv 가 자동 다운로드, `.python-version` 에 고정)
- 패키지 매니저: **uv** (poetry/pip 아님)
- 워크스페이스 구조: 루트 `pyproject.toml` + 단계별 멤버
- 인프라: 05단계에서 단일 Docker Compose 도입 예정 (Postgres/Redis/Kafka, profiles 토글)
- 사용자 배경: Java/Spring · Go 경험, Python 거의 처음 → README 의 _Java/Go 비교 섹션_ 이 학습 가속기

## 3단계에서 할 일 (다음 세션 첫 작업)

`03-libraries-tour/` — 자주 쓰는 라이브러리 투어:
- **pydantic v2** — 모델/검증 (Spring `@Valid` + Lombok 대응)
- **httpx** — 동기/비동기 HTTP 클라이언트
- **orjson** — 고성능 JSON 직렬화
- **jsonpath-ng** — JSON 문서 조작/쿼리, deep merge
- **structlog** 또는 **loguru** — 로깅
- **python-dateutil** / **zoneinfo** — 날짜/시간
- **python-dotenv** — 환경변수
- 부수 학습: PyPI 검색법, 라이브러리 평가 기준 (stars / 최근 릴리스 / 다운로드)

산출물 패턴 (01·02와 동일):
```
03-libraries-tour/
├── pyproject.toml        # 위 라이브러리들을 dependencies 에
├── Makefile              # make run / test / lint
├── README.md             # 학습 목표 / Java 비교 / 안티패턴 / TODO
├── src/                  # 라이브러리별 데모 모듈
└── tests/
```

루트 `pyproject.toml` 의 workspace members / dependencies / sources 에도 등록 필요.

## 진행 방식 권장 (이미 정착된 패턴)

1. **단계당 1세션** — 한 번에 다음 단계까지 가지 말고 체크인.
2. **사용자가 "이거 감이 안 잡힘" 류 질문하면 build-up 학습 모듈로 _확장_** (s02 컴프리헨션, s07 구조 분해 패턴).
3. **각 단계 완료 시 루트 `README.md` 의 체크리스트 ✅ 갱신**.
4. **`make all` 녹색이면 단계 완료**. 추가로 데모/CLI 동작도 직접 확인.

## 검증 명령 (지금 상태 확인용)

```bash
cd /Users/hyunmin.song/Desktop/bespin/fast-api

# 환경 동기화
uv sync

# 01 회귀
cd 01-python-basics && make all
# → 60 passed

# 02 회귀
cd ../02-package-structure && make all
# → 18 passed

# CLI 동작
uv run greeter hello Alice --locale en
# → Hello, Alice!
```
