# 05 단계 Makefile — 도커 명령 단축.
# 모든 명령은 _리포 루트_ 의 docker-compose.yml 을 사용 (-f ../docker-compose.yml).

.PHONY: up down ps logs config build pull restart \
        up-db up-cache up-kafka up-app up-all \
        psql redis-cli rpk-topics

# 기본: db + cache (가장 자주 쓰는 조합)
up: up-db up-cache

up-db:
	cd .. && docker compose --profile db up -d

up-cache:
	cd .. && docker compose --profile cache up -d

up-kafka:
	cd .. && docker compose --profile kafka up -d

# fastapi-hello 컨테이너로 띄우기 (build + run)
up-app:
	cd .. && docker compose --profile app up -d --build

# 전부
up-all:
	cd .. && docker compose --profile all up -d

down:
	cd .. && docker compose down

# 데이터까지 _완전_ 삭제 (주의)
down-clean:
	cd .. && docker compose down -v

ps:
	cd .. && docker compose ps

logs:
	cd .. && docker compose logs -f --tail 100

# YAML 합치기/검증 — 도커 데몬 없어도 일부 동작
config:
	cd .. && docker compose config

# 이미지 미리 받기 (느린 네트워크 환경에서 유용)
pull:
	cd .. && docker compose --profile all pull

build:
	cd .. && docker compose --profile app build

restart:
	cd .. && docker compose restart

# ---------- 컨테이너 안에 들어가서 빠르게 만져보기 ----------

psql:
	cd .. && docker compose exec db psql -U postgres -d learning

redis-cli:
	cd .. && docker compose exec cache redis-cli

# Redpanda 의 CLI (rpk) — 토픽 목록 등
rpk-topics:
	cd .. && docker compose exec kafka rpk topic list
