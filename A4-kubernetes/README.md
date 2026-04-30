# A4 — Kubernetes (raw manifests + Helm chart)

05 의 docker-compose 를 K8s 매니페스트와 Helm chart 로 _두 가지 방식_ 모두.

## 학습 목표

- **K8s 핵심 리소스** — Deployment / Service / Ingress / ConfigMap / Secret / StatefulSet / HPA
- **liveness vs readiness probe** (04 의 `/healthz` vs `/readyz` 활용)
- **rolling update** vs blue/green vs canary
- **Helm chart 구조** — `Chart.yaml` / `values.yaml` / `templates/` / `_helpers.tpl`
- **GitOps** 소개 — ArgoCD / Flux

## 디렉토리

```
A4-kubernetes/
├── Makefile                            # validate / apply / helm-* 단축
├── README.md
├── manifests/                           # raw YAML (kubectl apply)
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml                     # ⚠ 학습용 평문, 운영은 sealed-secrets
│   ├── postgres.yaml                   # StatefulSet + headless Service
│   ├── redis.yaml                      # Deployment + Service
│   └── tender-deployment.yaml          # Deployment + Service + HPA + Ingress
└── helm/tender/                         # Helm chart (템플릿화)
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── _helpers.tpl                # 공통 라벨 helper
        ├── configmap.yaml
        ├── secret.yaml
        ├── deployment.yaml
        ├── service.yaml
        ├── ingress.yaml
        └── hpa.yaml
```

## 실행 (로컬 클러스터 가정 — kind / minikube / Docker Desktop K8s)

### 사전 준비

```bash
# 클러스터 (셋 중 하나)
brew install kind && kind create cluster --name learning
# 또는 Docker Desktop 의 Kubernetes 활성화

# 도구
brew install kubernetes-cli helm kubeconform
```

### raw manifests

```bash
cd A4-kubernetes

make validate         # 문법 검증 (kubeconform 또는 kubectl dry-run)
make apply            # 클러스터에 적용
kubectl get pods -n tender
kubectl logs -n tender deployment/tender
make delete           # 정리
```

### Helm chart

```bash
make helm-lint        # chart 검증
make helm-template    # 렌더링 결과 _확인_ (실제 적용 X)
make helm-install     # 또는 helm upgrade --install
make helm-uninstall
```

## docker-compose vs K8s 매핑

| docker-compose | K8s 리소스 |
|---|---|
| `services:` | Deployment / StatefulSet / DaemonSet |
| `image:` | container `image` |
| `ports: "8000:8000"` | Service (ClusterIP / NodePort / LoadBalancer) + Ingress |
| `volumes:` | PersistentVolumeClaim + volumeMount |
| `environment:` | env: / envFrom: ConfigMap+Secret |
| `depends_on: condition: service_healthy` | initContainers + readinessProbe |
| `healthcheck:` | livenessProbe + readinessProbe |
| `profiles:` | namespace + label selector |
| `--scale app=3` | replicas: 3 + HPA |
| 컨테이너 호스트명 | Service name (DNS) |

## 다국 언어 / 도구 비교

| 개념 | 가장 가까운 비교 |
|---|---|
| **kubectl apply** | docker-compose up |
| **Helm** | npm 같은 _패키지 매니저 + 템플릿 엔진_ — 차트 = "K8s 의 npm 패키지" |
| **values.yaml** | 환경별 .env 또는 application-{profile}.yml (Spring) |
| **Kustomize** | _patch 기반_ overlay (Helm 의 대안 — 템플릿 X) |
| **ArgoCD / Flux** | GitOps — `git push` → 자동 배포 (Spotify Backstage 자리) |

## probe 가이드 — liveness vs readiness

| probe | 실패 시 | 용도 |
|---|---|---|
| **liveness** | Pod _재시작_ | 죽었는지 확인 (deadlock, 무한 루프) |
| **readiness** | Service 에서 _제외_ (재시작 X) | 트래픽 받을 준비 됐는지 (DB 연결 등) |
| **startup** (3.16+) | liveness 시작 _지연_ | 부팅 오래 걸리는 앱 |

본 매니페스트는 04 의 `/healthz` 를 _둘 다_ 에 사용. 운영급은 readiness 만 `/readyz` (DB 의존성 검사) 로 분리 — 10 단계 떡밥.

## 배포 전략

| 전략 | 특징 |
|---|---|
| **RollingUpdate** (기본) | 한 번에 N개씩 교체. 단순, 롤백 쉬움 |
| **Blue/Green** | 신규 환경 _전체_ 띄운 후 트래픽 _즉시_ 전환. 롤백 빠름 |
| **Canary** | 1% → 5% → 25% → 100% 점진 전환 — Argo Rollouts / Flagger |
| **Recreate** | 모두 죽이고 새로 — 짧은 다운타임 OK |

본 chart 는 RollingUpdate (`maxSurge: 1, maxUnavailable: 0`).

## 안티패턴

1. **`image: tag: latest`** — 어느 버전인지 모름. 항상 _명시 태그_ (`v1.2.3`, sha-abc).
2. **resources 누락** — 노드 자원 폭발 위험. 항상 `requests` + `limits`.
3. **루트 사용자로 실행** — 보안 사고 시 피해 ↑. `runAsNonRoot: true`.
4. **liveness probe 만 사용 + 무거운 부팅** — 재시작 루프. startup probe 또는 initialDelaySeconds.
5. **운영에서 클러스터 내부 Postgres** — 백업/HA 부담. 관리형 DB (RDS/Cloud SQL) 권장.
6. **Secret 평문 git 커밋** — 유출 위험. sealed-secrets / external-secrets / sops.
7. **Ingress TLS 누락** — 평문 HTTP. cert-manager + Let's Encrypt 자동.
8. **HPA 만 의존, Cluster Autoscaler 없음** — Pod 늘어도 _노드 부족_ 으로 Pending. 둘 다.
9. **Helm `--force`** — 리소스 _재생성_ 사고. 정상 흐름은 `upgrade --install` (idempotent).

## 운영급 추가 도구 (참고)

| 영역 | 도구 |
|---|---|
| GitOps | ArgoCD, Flux, Rancher Fleet |
| 배포 자동화 | Argo Rollouts (canary), Spinnaker |
| Secret 관리 | sealed-secrets, external-secrets-operator, sops, Vault |
| Service Mesh | Istio, Linkerd |
| 관측가능성 | Prometheus operator, Grafana, Loki, Jaeger/Tempo |
| Postgres HA | Crunchy Postgres Operator, Zalando Postgres Operator, Patroni |
| Kafka HA | Strimzi (Operator), Confluent Operator |

## 직접 해보기 TODO

- [ ] `kind create cluster` 후 `make apply` — 실제 동작 확인
- [ ] `kubectl port-forward svc/tender 8000:80 -n tender` 후 curl 로 healthz
- [ ] `make helm-template` 출력 확인 — values 가 어떻게 치환되는지
- [ ] `values-prod.yaml` 추가하고 `helm upgrade -f values-prod.yaml` 로 환경별
- [ ] Kustomize 로 같은 결과 — `kustomization.yaml` + `overlays/{dev,prod}/`
- [ ] Argo Rollouts 설치 → canary 배포 시뮬레이션
- [ ] `kubectl describe hpa tender -n tender` — HPA 동작 메트릭

## 다음 단계

**A5 — 보안 심화**. OWASP Top 10, mTLS, OAuth2 3rd party, 2FA/TOTP, Vault 시크릿 관리.
