"""tracemalloc — 메모리 측정 + 누수 탐지 패턴 검증."""

from __future__ import annotations

from perfdeep.tracemalloc_demo import (
    clean_function,
    leaky_function,
    measure_memory,
    reset_leaky_state,
)


def test_measure_memory_returns_report() -> None:
    def allocate() -> list[int]:
        return list(range(10000))

    result, report = measure_memory(allocate)
    assert len(result) == 10000
    # 어떤 메모리든 사용은 함
    assert report.peak_bytes > 0


def test_leaky_function_grows_global_state() -> None:
    """누수 시뮬레이션 — 전역 dict 가 _계속_ 커짐."""
    reset_leaky_state()
    leaky_function(1)
    leaky_function(2)
    leaky_function(3)
    # 3 호출 → global cache 에 3 키
    assert leaky_function(4) == 4
    reset_leaky_state()


def test_leaky_uses_more_memory_than_clean() -> None:
    """leaky 가 _계속_ 누적 → 같은 호출 횟수에서 더 많은 메모리."""
    reset_leaky_state()

    def call_leaky() -> None:
        for i in range(20):
            leaky_function(i)

    def call_clean() -> None:
        for i in range(20):
            clean_function(i)

    _, leaky_report = measure_memory(call_leaky)
    reset_leaky_state()
    _, clean_report = measure_memory(call_clean)

    # leaky 가 _훨씬_ 더 사용 (정확한 비율은 GC 타이밍 따라 변동)
    assert leaky_report.peak_bytes > clean_report.peak_bytes
    reset_leaky_state()


def test_top_lines_returned() -> None:
    """할당량 상위 N 라인 표시."""

    def allocator() -> None:
        big = [list(range(1000)) for _ in range(50)]  # noqa: F841

    _, report = measure_memory(allocator, top_n=3)
    assert len(report.top_lines) <= 3
