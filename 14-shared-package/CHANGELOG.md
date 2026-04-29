# Changelog

본 프로젝트는 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르며,
버전 관리는 [SemVer](https://semver.org/lang/ko/) 를 따릅니다.

## [Unreleased]

## [0.1.0] - 2026-04-29

### Added
- `ApiEnvelope[T]` 공통 응답 envelope (07 단계에서 추출)
- `ErrorCode` enum + `DomainError` 베이스 (07 단계에서 추출)
- `install_exception_handlers(app)` — 도메인/검증/HTTP/미처리 4단 핸들러
- `CorrelationIdMiddleware` + `install_correlation_middleware(app)` (12 단계)
- `ResilientClient` + `make_breaker_factory` — httpx + tenacity + purgatory (12 단계)
- `configure_logging(env, log_level)` — structlog dev/prod 분리
