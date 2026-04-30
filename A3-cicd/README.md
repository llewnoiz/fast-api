# A3 — CI/CD 파이프라인 (GitHub Actions)

본편의 _모든 단계_ 가 자동으로 lint/test/build/deploy 되도록.

## 학습 목표

- **GitHub Actions** 워크플로 구조 (jobs, steps, matrix)
- **잡 분리** — 빠른 PR 검증 (unit) vs 전체 (integration)
- **`testcontainers` on CI** — 도커 내장 러너 활용
- **도커 멀티 플랫폼 빌드** (amd64 + arm64) + GHCR push
- **태그 기반 패키지 배포** — 14 fastapi-common 자동 wheel 배포
- **Dependabot** — 의존성 자동 업데이트 PR

## 디렉토리 / 파일

```
fast-api/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # lint + unit + integration
│   │   ├── docker.yml              # 도커 이미지 build + push to GHCR
│   │   └── release-package.yml     # fastapi-common wheel 자동 배포
│   └── dependabot.yml              # 의존성 자동 업데이트
└── A3-cicd/
    └── README.md                   (지금 보고 있는 파일)
```

## 다국 언어 비교

| 도구 | 비교 |
|---|---|
| **GitHub Actions** | GitLab CI, CircleCI, Jenkins (Pipeline) |
| **`uses: actions/...`** | GitLab include, Jenkins shared library |
| **GHCR (ghcr.io)** | Docker Hub, GitLab Container Registry, AWS ECR |
| **Dependabot** | renovate-bot (더 풍부), Snyk |
| **OIDC 인증** | GitLab OIDC, IAM Role for Service Account (K8s) |

## 워크플로 3가지

### 1) `ci.yml` — 메인 CI

```
push to main / PR
   │
   ├── lint-and-typecheck (ruff + mypy)
   ├── unit-tests          (도커 무관 — 빠름)
   └── integration-tests   (testcontainers — 1~2분)
```

**병렬 잡** — 3개가 _동시_ 실행. 한 잡 실패해도 다른 잡 계속.

**`concurrency`** — 같은 PR 에 여러 푸시 → 진행 중 빌드 자동 취소 (자원 절약).

### 2) `docker.yml` — 이미지 빌드 + push

```
push to main / git tag v*
   │
   └── build-app
        ├── docker buildx (amd64 + arm64)
        ├── ghcr.io 로그인 (GITHUB_TOKEN)
        └── tag: branch / tag / sha
```

**`docker/metadata-action`** — 자동 태그 (예: `main`, `v1.0`, `sha-abc1234`).

**GHA 캐시** — `cache-from/to: type=gha` 로 빌드 시간 50%+ 단축.

### 3) `release-package.yml` — fastapi-common 자동 배포

```
git tag fastapi-common-v0.2.0 + push
   │
   └── build-and-publish
        ├── uv build (wheel + sdist)
        └── GitHub Releases 에 첨부
        # 또는 사내 PyPI 에 publish (커멘트 처리됨)
```

태그 _이름 컨벤션_ 으로 _어떤 패키지의 어떤 버전_ 인지 표시. 14 의 SemVer 정책과 결합.

## OIDC vs 시크릿 — 운영 권장

**나쁜 패턴**:
```yaml
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}    # ❌ 장기 시크릿
```

**좋은 패턴 — OIDC**:
```yaml
permissions:
  id-token: write   # GitHub OIDC 토큰 발급

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123:role/MyRole
      aws-region: ap-northeast-2
```

GitHub Actions → AWS IAM Trust Policy → 임시 자격증명 발급. **장기 시크릿 _없음_**.

## 잡 분리 가이드

| 잡 | 트리거 | 시간 | 목적 |
|---|---|---|---|
| **lint-and-typecheck** | 매 push/PR | 30초 | 코드 스타일 + 타입 |
| **unit-tests** | 매 push/PR | 1분 | 빠른 피드백 |
| **integration-tests** | 매 push/PR | 2~5분 | 도커 의존 검증 |
| **docker build** | main/tag | 3~10분 | 배포 산출물 |
| **deploy** | tag (별도 워크플로) | 1~2분 | 운영 적용 |

PR 마다 _빠른 피드백 (lint+unit)_ 우선. integration 은 _병렬_ 또는 _태그/main 에서만_ 줄여서 비용 절감.

## Pre-commit + CI 이중 안전망

본 프로젝트엔 02 단계에서 도입한 `.pre-commit-config.yaml` 이 _커밋 시점_ 에 ruff/mypy 실행. CI 는 _그래도 한 번 더_ 검증 — 누군가 `--no-verify` 우회해도 잡힘.

```bash
# 로컬 설정 (한 번)
uv run pre-commit install

# 전체 파일 수동 실행
uv run pre-commit run --all-files
```

## 안티패턴

1. **시크릿 평문 노출** — `echo $TOKEN` 으로 로그에 찍힘. `set +x` 로 마스킹.
2. **`secrets.*` 컨텍스트 밖에서 사용** — `if: ${{ secrets.X }}` 같은 표현식 평가 X. 잡 안에서만.
3. **모든 push 마다 도커 빌드** — 비용 ↑. main / tag 만.
4. **runner OS 무한 자유 — 의도치 않은 변경** — `runs-on: ubuntu-latest` _대신_ `ubuntu-24.04` 핀.
5. **action 버전 `@latest` 또는 `@main`** — 공급망 위험. `@v4` 같은 _major 핀_ + dependabot 자동 갱신.
6. **OIDC 안 쓰고 장기 access key** — 유출 시 _영구_ 위험. 무조건 OIDC.
7. **CI 에서 _운영 DB_ 마이그레이션** — 사고 위험. 마이그레이션은 _별도_ 수동 또는 별도 워크플로.
8. **모든 의존성 자동 머지** — 메이저 업그레이드는 _깨짐_. 본 dependabot 설정도 minor/patch 만.

## 직접 해보기 TODO

- [ ] 본 워크플로를 _실제_ GitHub 저장소에 push 해서 동작 확인
- [ ] `act` 도구로 _로컬_ 실행 (`brew install act && act -j unit-tests`)
- [ ] `pre-commit autoupdate` — pre-commit 의 fix 도구 버전 갱신
- [ ] Slack/Discord 알림 — 빌드 실패 시 webhook
- [ ] **release-please** 또는 **semantic-release** — 커밋 메시지 기반 자동 버전 + CHANGELOG
- [ ] **trivy** / **grype** — 도커 이미지 보안 스캔 추가
- [ ] 운영 배포 — `deploy.yml` 워크플로 (Cloud Run / ECS / K8s rollout)
- [ ] **canary 배포** — `deploy.yml` 의 단계적 트래픽 이동

## 검증 — 로컬에서

GitHub Actions 워크플로는 _GitHub 에 push 해야_ 진짜 실행. 로컬에선 YAML 문법만 검증 가능:

```bash
# YAML 문법 검사
yamllint .github/

# 또는 act 도구로 _로컬 실행_ (도커 필요)
brew install act
act -j unit-tests --container-architecture linux/amd64

# pre-commit 은 로컬에서 동작
uv run pre-commit run --all-files
```

## 다음 단계

**A4 — Kubernetes**. 05 의 docker-compose 를 K8s manifests + Helm 으로 전환. 운영 배포의 진짜 모습.
