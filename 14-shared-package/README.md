# 14 — fastapi-common: 사내 공통 패키지 + 팀 공유

06~13 에서 만든 _공통 코드_ 를 별도 라이브러리로 추출. 사내 다른 서비스가 `pip install` (혹은 `uv add`) 로 가져다 쓸 수 있게.

## 학습 목표

- **uv workspace** 활용 (이미 사용 중) — 모노레포 내부 의존성
- **사내 배포 옵션 3가지** — git+ssh / 사내 PyPI / wheel 직접 배포
- **공개 API surface 설계** — `__init__.py` 의 `__all__`
- **SemVer + CHANGELOG** — 버전 관리 + 호환성 정책
- **wheel/sdist 빌드** — `uv build`
- **`uv tool install`** — 다른 환경 install 시뮬레이션

## 무엇을 추출했나

| 단계 | 추출된 모듈 | 역할 |
|---|---|---|
| 07 | `envelope.py`, `errors.py`, `handlers.py` | ApiEnvelope[T], ErrorCode, DomainError, 전역 핸들러 |
| 12 | `correlation.py` | X-Request-ID 미들웨어 + structlog contextvars |
| 12 | `http_client.py` | ResilientClient (httpx + tenacity + purgatory) |
| 04 / 12 | `logging_setup.py` | structlog dev/prod 분리 |

## 디렉토리

```
14-shared-package/
├── pyproject.toml          # name=fastapi-common, version=0.1.0
├── README.md               (← 지금 보고 있는 파일)
├── CHANGELOG.md            # Keep a Changelog 형식
├── Makefile                # make build / install-global / test / lint
├── src/fastapi_common/
│   ├── __init__.py         # 공개 API surface (__all__) + __version__
│   ├── envelope.py
│   ├── errors.py
│   ├── handlers.py
│   ├── correlation.py
│   ├── http_client.py
│   └── logging_setup.py
└── tests/
    └── test_lib.py         # 공개 API 안정성 + 미니 FastAPI 앱 통합
```

## 실행

```bash
cd .. && uv sync && cd 14-shared-package

make all                   # ruff + mypy + pytest
make build                 # dist/fastapi_common-0.1.0-py3-none-any.whl + tar.gz
ls dist/                   # 산출물 확인

# 다른 환경에 install 시뮬레이션
make install-global        # uv tool install --from . fastapi-common
# 다른 디렉토리에서:
#   uv add /path/to/dist/fastapi_common-0.1.0-py3-none-any.whl
#   from fastapi_common import ApiEnvelope, ResilientClient
make uninstall-global
```

## 사용자 (사내 다른 서비스) 입장에서

```python
from fastapi import FastAPI
from fastapi_common import (
    ApiEnvelope,
    DomainError,
    ErrorCode,
    ResilientClient,
    install_correlation_middleware,
    install_exception_handlers,
    make_breaker_factory,
    success,
)

app = FastAPI()
install_correlation_middleware(app)
install_exception_handlers(app)

@app.get("/items/{id}")
async def get_item(id: int) -> ApiEnvelope[dict]:
    if id == 999:
        raise DomainError(code=ErrorCode.NOT_FOUND, message="missing", status=404)
    return success({"id": id, "name": "x"})
```

## 사내 배포 옵션 — 3가지

### 옵션 1: `git+ssh://` 직접 의존성 (가장 단순)

```toml
# 사용 측 pyproject.toml
[project]
dependencies = [
    "fastapi-common @ git+ssh://git@github.example.com/myorg/fastapi-common.git@v0.1.0",
]
```

장점:
- 추가 인프라 없음
- 사내 GitHub / GitLab / Gitea 그대로
- 태그/브랜치/커밋 기반 고정 가능

단점:
- _빌드_ 매번 수행 (느림)
- 의존성 그래프 큰 모노레포에 부담
- 익명 사용자 cache 불가 (각자 clone)

### 옵션 2: 사내 PyPI (devpi, pypiserver, AWS CodeArtifact)

```bash
# 빌드
make build
# 업로드 (twine 또는 uv publish)
twine upload --repository-url https://pypi.internal/simple dist/*

# 사용 측 — 인덱스 추가
[tool.uv]
index-url = "https://pypi.internal/simple"
```

도구 비교:

| 도구 | 호스팅 | 인증 | 비교 |
|---|---|---|---|
| **devpi** | self-hosted | 단순 | npm Verdaccio 자리 |
| **pypiserver** | self-hosted | 단순 | 가장 가벼움 |
| **AWS CodeArtifact** | managed | IAM | npm enterprise (managed) |
| **GitHub Packages** | managed | GH token | npm packages |
| **GCP Artifact Registry** | managed | IAM | 동일 |

### 옵션 3: wheel 직접 배포

```bash
make build              # dist/*.whl
# scp / S3 / 사내 NAS 에 올리기

# 사용 측
[project]
dependencies = [
    "fastapi-common @ file:///shared/wheels/fastapi_common-0.1.0-py3-none-any.whl",
]
```

가장 _원시적_. CI 자동화 필요.

### 권장 — 규모별

| 규모 | 추천 |
|---|---|
| 개인 / 작은 팀 | git+ssh (옵션 1) |
| 중규모 (10+ 서비스) | 사내 PyPI (devpi or CodeArtifact) |
| 대규모 / 엔터프라이즈 | managed (CodeArtifact / GH Packages) |

## SemVer 정책

| 변경 | 버전 |
|---|---|
| `ErrorCode.NEW_CODE` 추가 | 0.1.0 → 0.2.0 (MINOR) |
| 새 함수 / 클래스 추가 | 0.1.0 → 0.2.0 (MINOR) |
| 버그 수정 | 0.1.0 → 0.1.1 (PATCH) |
| `ErrorCode.NOT_FOUND` _이름 변경_ | 0.1.0 → 1.0.0 (MAJOR) |
| `ApiEnvelope.code` 타입 변경 | 0.1.0 → 1.0.0 (MAJOR) |
| `__init__` 의 함수 _제거_ | 0.1.0 → 1.0.0 (MAJOR) |

**0.x 시기**는 _불안정_ — 0.x → 0.(x+1) 도 깨짐 변경 가능. 1.0.0 부터 _안정 약속_.

## 공개 API surface — `__init__.py` 의 의미

```python
from fastapi_common.envelope import ApiEnvelope, success
from fastapi_common.errors import DomainError, ErrorCode
# ... 등등
__all__ = [...]
```

**규칙**:
- `__init__.py` 에 export 된 심볼만 _공개_. 그 외는 _내부_.
- 공개 심볼 _제거_ = MAJOR 버전. 추가 = MINOR.
- 사용자는 `from fastapi_common import X` 만 권장 — 내부 모듈 직접 import 비권장.
- 내부 구조 (`fastapi_common.handlers.py` 의 함수 위치) 는 _자유롭게_ 변경 가능.

## CHANGELOG — 변경 기록

`CHANGELOG.md` 에 _Keep a Changelog_ 형식. PR 마다 `[Unreleased]` 섹션에 추가, 릴리스 시 버전 섹션으로 이동.

```markdown
## [Unreleased]
### Added
- `ApiEnvelope.warnings` 필드

## [0.2.0] - 2026-05-15
### Added
- ErrorCode.RATE_LIMITED
### Fixed
- ResilientClient 의 timeout 로깅 누락
```

## 안티패턴

1. **공개 API 마음대로 변경** — 사용자 _전부_ 깨짐. SemVer + deprecation warning 절차.
2. **`__all__` 누락** — `from fastapi_common import *` 시 모든 내부 노출. 명시 권장.
3. **무거운 의존성을 라이브러리에 박기** — 사용자 install 비용 ↑. _최소_ 의존성 + `[project.optional-dependencies]` 활용 (예: `auth` 그룹).
4. **`requirements.txt` 로 라이브러리 배포** — 의존성 _고정_ 되어 사용자 환경 충돌. lib 은 _범위 (>=)_, 앱은 _고정_.
5. **버전 안 올리고 새 코드 배포** — 캐시된 사용자가 _옛 버전_ 받음. 변경 시 항상 버전 ↑.
6. **CHANGELOG 없이 변경** — 사용자가 _뭐가 바뀌었는지_ 모름. 릴리스마다 작성.
7. **`pyproject.toml` 의 `description` / `readme` / `license` 누락** — PyPI 노출 안 됨, 빌드 경고.
8. **모노레포 안에서 _상대 경로_ import 로 결합** — 사용 측이 같은 구조여야 동작. `fastapi_common.envelope` 처럼 _자기 패키지_ 절대 경로.

## 직접 해보기 TODO

- [ ] 새 ErrorCode `RATE_LIMITED` 추가 → CHANGELOG 갱신 → 0.1.0 → 0.2.0 → `make build` 새 wheel
- [ ] `auth` optional dep 활용 — `from fastapi_common.auth import OAuth2Bearer` 같은 모듈 추가
- [ ] `make install-global` 후 _다른 디렉토리_ 에서 `uv add fastapi_common` 시도
- [ ] `git tag v0.1.0` 후 `git+ssh://...@v0.1.0` 형태로 의존성 추가
- [ ] `[project.entry-points."fastapi_common.plugins"]` — 플러그인 시스템 설계
- [ ] `pip-audit` 으로 의존성 보안 취약점 검사
- [ ] `py.typed` 마커 파일 추가해서 mypy 가 stub 으로 인식하게

## 다음 단계

**15 — 통합 미니 프로젝트**. fastapi-common (14) 을 의존성으로 사용 + 04~13 의 모든 개념을 결합한 작은 _주문/입찰(tender) 서비스_. 끝!
