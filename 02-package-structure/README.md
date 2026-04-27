# 02 — Python 패키지/모듈 구조

01 단계는 _스크립트_ 의 모음이었다. 02 는 **진짜 배포 가능한 패키지** 를 만든다 — `pyproject.toml` 로 메타데이터를 선언하고, src layout 을 따르고, 콘솔 스크립트 entry point 를 등록하고, 외부 사용자가 `pip install` 한 것처럼 import 가 동작하게 한다.

## 학습 목표

- **src layout vs flat layout** — 왜 src 가 권장되는가
- **`pyproject.toml`** (PEP 621) — 패키지 메타데이터 작성법
- **콘솔 스크립트 entry point** — `[project.scripts]` 로 CLI 등록 → `uv run greeter ...`
- **절대 vs 상대 import** — 언제 어느 걸 쓰는가
- **순환 import** — 함정과 회피 전략 3가지
- **린트 / 타입 / 훅 도구** — `ruff`, `mypy`, `pre-commit`

## 실행

```bash
# 루트에서 한 번 (workspace 전체 의존성 동기화 + 콘솔 스크립트 자동 설치)
cd .. && uv sync
cd 02-package-structure

make run                          # hello + shout 데모
make demo-hello FILE=...          # (없음, hello/shout 서브 타깃 사용)
uv run greeter hello Alice --locale en   # ← 콘솔 스크립트 직접 호출

make test                         # pytest
make lint                         # ruff
make typecheck                    # mypy
make build                        # wheel/sdist 만들기 (14 단계 떡밥)
```

## 패키지 구조 — src layout

```
02-package-structure/
├── pyproject.toml          # ← 메타데이터 + 빌드 설정 + entry point
├── Makefile
├── README.md
├── src/
│   └── greeter/            # ← _진짜_ 패키지 (배포되는 코드)
│       ├── __init__.py     # 공개 API surface
│       ├── core.py         # 비즈니스 로직 (greet/shout/make_card)
│       ├── cli.py          # 콘솔 스크립트 진입점
│       ├── _internal.py    # 내부 헬퍼 (`_` 접두 = 비공개)
│       └── circular_demo.py  # 순환 import 안티패턴 + 회피 전략 (주석)
└── tests/
    └── test_greeter.py     # 설치된 greeter 를 import 해서 테스트
```

### src layout vs flat layout

| 형태 | 구조 | 장단점 |
|---|---|---|
| **src layout** (이 단계) | `src/greeter/...` | 테스트가 _설치된 패키지_ 를 강제로 import → 빌드 결함 조기 발견. 권장. |
| flat layout | `greeter/...` (루트 직속) | 단순하지만 cwd 의존 import 가 우연히 동작해서 빌드 시 깨질 수 있음 |

**핵심**: src layout 에선 `tests/` 가 `from greeter import ...` 만으로 동작하려면 _패키지가 진짜로 설치되어 있어야_ 한다. 01 단계의 `tests/conftest.py` 처럼 `sys.path` 를 조작하지 않는다 — `uv sync` 가 알아서 editable install 해줌.

## `pyproject.toml` 핵심 필드

```toml
[project]
name = "greeter"                           # PyPI 이름 (설치 시 사용)
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []                          # 런타임 의존성

[project.scripts]
greeter = "greeter.cli:main"               # ← `greeter` 명령 = `greeter.cli.main()` 호출

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/greeter"]                 # wheel 에 포함될 폴더
```

`[project.scripts]` 한 줄로 `uv sync` 시점에 `.venv/bin/greeter` 가 생성되어 PATH 에 들어옵니다.

## Java / Maven 비교

| 개념 | Python | Java/Maven |
|---|---|---|
| 빌드 파일 | `pyproject.toml` | `pom.xml` / `build.gradle` |
| 그룹/이름 | `name`, `version` | `groupId`, `artifactId`, `version` |
| 빌드 backend | `hatchling`, `setuptools`, `flit` | Maven, Gradle |
| 콘솔 스크립트 | `[project.scripts]` | `MANIFEST.MF` `Main-Class` |
| 산출물 | `wheel` (`.whl`), `sdist` (`.tar.gz`) | `jar` |
| 의존성 그룹 | `[dependency-groups]` (uv) | `<scope>test</scope>` |
| 패키지 레지스트리 | PyPI / 사내 PyPI | Maven Central / 사내 Nexus |
| 코드 스타일 | PEP 8 + `ruff` | `Spotless` / `Checkstyle` |
| 정적 분석 | `mypy` (타입), `ruff` (린트) | 컴파일러 + `SpotBugs` |
| 사전 커밋 훅 | `pre-commit` | git hooks 직접 / `Husky-like` 도구 |

## 절대 vs 상대 import — 언제 어느 걸?

### 상대 import (`from .core import greet`)

같은 패키지 _안쪽_ 에서 권장.

```python
# src/greeter/cli.py
from .core import greet, shout    # ← 같은 greeter 패키지 내부
```

장점:
- 패키지 이름이 바뀌어도 import 안 깨짐
- "이건 같은 패키지의 자산" 의도 명확

한계:
- `..a.b.c` 처럼 깊어지면 가독성 ↓
- 모듈을 _스크립트_ 로 직접 실행하면 작동 X (`__main__` 일 때 패키지 컨텍스트 없음)

### 절대 import (`from greeter.core import greet`)

외부에서 / 깊은 경로 / 진입점 스크립트 에선 절대.

```python
# tests/test_greeter.py
from greeter import greet     # ← 외부 사용자 관점
```

### 일반 규칙

- 같은 패키지 안: 상대 (`from .core import ...`)
- 다른 패키지: 절대 (`from greeter.core import ...`)
- `__init__.py` 의 공개 API 재export: 둘 다 OK, _절대_ 가 약간 더 명시적
- `from __future__ import annotations` 와 함께 쓰면 타입 힌트 import 는 거의 항상 안전

## 순환 import — 함정과 회피 3가지

상세 코드는 `src/greeter/circular_demo.py` 주석 참고.

| 전략 | 핵심 | 언제 |
|---|---|---|
| **공통 의존성을 제3 모듈로** | 두 모듈이 _같은 외부 모듈_ 만 의존하게 | 가장 깔끔, 설계 차원 해결 |
| **지연(lazy) import** | 함수 _안에서_ import | 빠른 패치, 핫 패스가 아닐 때 |
| **`TYPE_CHECKING` 가드** | 런타임 import 회피, 타입만 사용 | 타입 힌트 전용 import |

`from __future__ import annotations` 를 모든 파일 맨 위에 두면 어노테이션이 자동으로 문자열이 되어서 `TYPE_CHECKING` 없이도 대부분 해결됩니다.

## 도구 — ruff / mypy / pre-commit

세 도구 모두 _루트 `pyproject.toml`_ 에 설정되어 있어 모든 단계가 공유합니다.

| 도구 | 역할 | Java 자리 |
|---|---|---|
| **ruff** | 린트 + 자동 포맷 + import 정렬. 매우 빠름 (Rust 작성). | Spotless / Checkstyle / Prettier |
| **mypy** | 정적 타입 검사 (런타임 영향 X). | 컴파일러의 타입 검사 |
| **pre-commit** | git commit 직전에 훅 실행 (lint/format/typecheck/secrets 검사). | husky / lefthook |

### pre-commit 도입

루트 `.pre-commit-config.yaml` 에 훅 정의됨. 사용:

```bash
# 한 번만 — git hook 으로 설치
uv run pre-commit install

# 수동 실행 (전체 파일)
uv run pre-commit run --all-files
```

이후 `git commit` 시 자동으로 ruff/mypy 가 돌고, 실패하면 commit 차단.

## 안티패턴

1. **`__init__.py` 에 _무거운_ 코드** — `import greeter` 가 느려짐. 가벼운 메타데이터/재export 만.
2. **`from greeter import *`** — 네임스페이스 오염, IDE 가 추적 어려움. `__all__` 정의해도 _명시 import_ 권장.
3. **flat layout + cwd 의존 import** — 로컬에선 동작하지만 `pip install` 후 _안_ 됨.
4. **순환 import 를 try/except 로 가림** — 진짜 문제(설계 결함) 를 숨김. 위 회피 전략 적용.
5. **상대 import 만 고집** — `..a..b` 처럼 깊어지면 절대로 가는 게 가독성 ↑.

## 직접 해보기 TODO

- [ ] `src/greeter/__main__.py` 추가 → `python -m greeter hello Alice` 동작하게 하기
- [ ] `core.py` 에 `farewell(name, locale)` 함수 추가, `__init__.py` 에 export, 테스트 추가
- [ ] `make build` 후 생성된 `dist/*.whl` 안을 `unzip -l` 로 들여다보고 어떤 파일이 들어갔는지 확인
- [ ] `uv tool install --from . greeter` 로 _전역_ CLI 설치 → 다른 디렉토리에서 `greeter hello Alice` 동작 확인 (지울 땐 `uv tool uninstall greeter`)
- [ ] 일부러 순환 import 만들어 ImportError 확인 → `circular_demo.py` 의 회피 전략 1번으로 풀기
- [ ] `ruff check --fix` / `ruff format` 차이 체험
