.PHONY: validate apply delete helm-lint helm-template helm-install helm-uninstall

# ============================================================================
# raw manifests (kubectl)
# ============================================================================

# 매니페스트 _문법_ 검증 — 클러스터 없이도 가능 (kubeconform 추천)
validate:
	@if command -v kubeconform >/dev/null 2>&1; then \
		kubeconform -summary manifests/; \
	else \
		echo "⚠ kubeconform 없음. 'brew install kubeconform' 권장. kubectl 으로 dry-run 시도:"; \
		kubectl apply --dry-run=client -f manifests/; \
	fi

# 실제 클러스터에 적용 (현재 kubectl context 에)
apply:
	kubectl apply -f manifests/

delete:
	kubectl delete -f manifests/ --ignore-not-found

# ============================================================================
# Helm
# ============================================================================

helm-lint:
	helm lint helm/tender

# 렌더링 결과 _확인_ (실제 적용 X)
helm-template:
	helm template tender helm/tender

helm-install:
	helm upgrade --install tender helm/tender \
		--namespace tender --create-namespace

helm-uninstall:
	helm uninstall tender --namespace tender
