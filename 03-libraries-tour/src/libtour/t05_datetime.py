"""t05 — datetime + zoneinfo + dateutil: 시간 다루기.

비교:
    JS:        Date (구식, 함정 많음), Temporal (제안), date-fns, dayjs
    Kotlin:    java.time (LocalDateTime / ZonedDateTime / Instant) — Python 과 _가장_ 유사
    Java 8+:   java.time (Joda-Time 후계자)
    Go:        time 패키지

Python 표준 도구:
    datetime.datetime   — 날짜+시간
    datetime.date       — 날짜만
    datetime.timedelta  — 차이
    zoneinfo.ZoneInfo   — IANA 타임존 (3.9+, 표준 라이브러리)
    dateutil            — 외부 라이브러리, ISO 파싱·상대 시간·반복 규칙 등 보조

가장 큰 함정 — **naive vs aware**:
    naive:  타임존 정보 _없음_ ─ 위험. 비교/저장 시 사고 빈발
    aware:  타임존 정보 _있음_ ─ 권장. 항상 UTC 또는 명시 타임존

규칙:
    - 코드 내부 / DB 저장: **UTC aware** 로 통일
    - 사용자 표시: **그 사람 타임존** 으로 변환

이 모듈에서:
    1. now() 의 두 가지 — naive vs aware
    2. ISO 8601 파싱
    3. 타임존 변환
    4. 차이 계산 (timedelta)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil.parser import isoparse

# ============================================================================
# 1) naive vs aware
# ============================================================================
#
# Kotlin 비교:
#   LocalDateTime.now()       ← naive (Java)
#   ZonedDateTime.now()       ← aware
#   Instant.now()             ← UTC aware (가장 권장)
# ============================================================================


def demo_naive_vs_aware() -> None:
    naive = datetime.now()                       # ❌ tzinfo=None — 위험
    aware_utc = datetime.now(UTC)                # ✅ tzinfo=UTC
    aware_seoul = datetime.now(ZoneInfo("Asia/Seoul"))

    print("naive   :", naive, " tz:", naive.tzinfo)
    print("aware UTC:", aware_utc, " tz:", aware_utc.tzinfo)
    print("aware KST:", aware_seoul, " tz:", aware_seoul.tzinfo)

    # naive 끼리 / aware 끼리만 비교 가능 — 섞으면 TypeError
    try:
        _ = naive < aware_utc                    # ❌
    except TypeError as e:
        print("섞으면:", e)


# ============================================================================
# 2) ISO 8601 파싱 — `2026-04-28T12:34:56+09:00`
# ============================================================================
#
# 표준 datetime.fromisoformat 도 _3.11+_ 부터 _대부분_ 의 ISO 8601 처리.
# 그래도 dateutil.parser.isoparse 가 _더 관대_ — 다양한 입력 케이스 지원.
# ============================================================================


def parse_iso_8601(s: str) -> datetime:
    """입력이 어떤 형태든 aware datetime 으로 파싱."""
    dt = isoparse(s)
    if dt.tzinfo is None:
        # tz 정보 없는 입력은 UTC 로 간주 (도메인 규칙에 따라 KST 일 수도)
        dt = dt.replace(tzinfo=UTC)
    return dt


# ============================================================================
# 3) 타임존 변환 — astimezone
# ============================================================================
#
# Kotlin: ZonedDateTime.toLocalDateTime() / withZoneSameInstant
# JS:     Intl.DateTimeFormat 로 표시만, 실제 변환은 Temporal 또는 dayjs-tz
# ============================================================================


def to_seoul(dt: datetime) -> datetime:
    """어떤 aware datetime 이든 KST 로 변환. naive 면 ValueError."""
    if dt.tzinfo is None:
        raise ValueError("naive datetime — tzinfo 가 필요합니다")
    return dt.astimezone(ZoneInfo("Asia/Seoul"))


# ============================================================================
# 4) timedelta — 차이 / 산술
# ============================================================================


def days_between(a: datetime, b: datetime) -> int:
    delta: timedelta = abs(a - b)
    return delta.days


def main() -> None:
    print("=== 1) naive vs aware ===")
    demo_naive_vs_aware()

    print("\n=== 2) ISO 8601 파싱 ===")
    samples = [
        "2026-04-28T12:34:56+09:00",
        "2026-04-28T03:34:56Z",
        "2026-04-28T12:34:56",        # tz 없음 → UTC 로 처리
    ]
    for s in samples:
        print(f"  {s} → {parse_iso_8601(s)}")

    print("\n=== 3) 타임존 변환 ===")
    utc_now = datetime.now(UTC)
    print("UTC    :", utc_now)
    print("→ KST  :", to_seoul(utc_now))

    print("\n=== 4) timedelta ===")
    a = datetime(2026, 1, 1, tzinfo=UTC)
    b = datetime(2026, 4, 28, tzinfo=UTC)
    print(f"{a.date()} ↔ {b.date()} = {days_between(a, b)}일")


if __name__ == "__main__":
    main()
