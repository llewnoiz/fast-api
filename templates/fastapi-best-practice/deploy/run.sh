#!/usr/bin/env sh
# 운영 uvicorn 실행 — proxy 헤더 + worker 수 환경변수.
#
# `--proxy-headers` + `--forwarded-allow-ips` ── 프록시 (ALB/Nginx) 뒤에서 진짜 client IP 추출.
# `WORKERS` ── 보통 (2 * vCPU + 1) 권장. K8s pod 1 worker + 다수 replica 도 흔함.
set -e

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WORKERS:-2}" \
  --proxy-headers \
  --forwarded-allow-ips '*'
