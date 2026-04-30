# Changelog

본 문서는 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 형식을 따른다.
버전은 [Semantic Versioning](https://semver.org/spec/v2.0.0.html) 준수.

## [Unreleased]

## [0.1.0] - 2026-04-30

### Added
- 초기 템플릿: FastAPI + Postgres + Redis + JWT 인증 + ApiEnvelope + correlation-id + 구조화 로그.
- 도메인: users (signup / login / me) + items (CRUD + owner 가드 + cache-aside).
- 인프라: Docker multi-stage, docker-compose (db + cache profile), GitHub Actions (lint+typecheck+unit+integration / GHCR push).
- 테스트: testcontainers Postgres + Redis 통합 테스트, asgi-lifespan, unit/integration 분리.
- 문서: README (한국어, Rename guide + Pitfalls), MIT LICENSE.
