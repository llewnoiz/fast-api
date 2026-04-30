"""tracemalloc — 메모리 할당 추적.

용도:
    - 메모리 _누수_ 탐지 (시간이 갈수록 RSS 증가)
    - 어떤 _라인_ / _파일_ 이 메모리 많이 먹는지
    - snapshot _diff_ — "이 시점부터 _얼마_ 더 늘었나"

vs `memray`:
    tracemalloc: _내장_, 가벼움, snapshot diff 기본.
    **memray**: _Bloomberg_ 작품. 더 강력 — flame graph, native 메모리, 분산.

운영 인시던트 (메모리 누수):
    1. RSS 그래프로 _증가 추세_ 발견 (Prometheus container_memory_rss)
    2. 의심 시간대에 tracemalloc snapshot 두 번 (5분 간격)
    3. snapshot diff 로 _증가한 위치_ 추적
    4. heap 분석 — 같은 객체 누적인지, 같은 라인이 매번 새로 만드는지
"""

from __future__ import annotations

import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass
class MemoryReport:
    current_bytes: int  # 추적 종료 시점 _현재_ 사용
    peak_bytes: int  # _최대_ 사용
    top_lines: list[tuple[str, int]]  # (파일:라인, 크기)


def measure_memory[T](fn: Callable[[], T], *, top_n: int = 5) -> tuple[T, MemoryReport]:
    """`fn()` 호출 동안 _할당된 메모리_ 측정 + 상위 N 라인.

    `tracemalloc.start()` 부터 `stop()` 까지 _모든 할당_ 추적.
    오버헤드: 보통 2~3x 느려짐 — 운영에선 _필요할 때만_.
    """
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    result = fn()
    snapshot_after = tracemalloc.take_snapshot()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # diff 분석 ── 이 함수 _동안_ 늘어난 위치
    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    top: list[tuple[str, int]] = []
    for stat in stats[:top_n]:
        # frame.filename:lineno + size
        frame = stat.traceback[0]
        top.append((f"{frame.filename}:{frame.lineno}", stat.size_diff))

    return result, MemoryReport(current_bytes=current, peak_bytes=peak, top_lines=top)


# ── 시연: _누수_ 시뮬레이션 ──
_global_cache: dict[int, list[int]] = {}


def leaky_function(n: int) -> int:
    """전역 dict 에 _계속_ 추가 — 호출할 때마다 메모리 ↑.

    실제 누수 사례:
        - 캐시 _만료 없음_ (TTL X)
        - 이벤트 리스너 _해제 안 됨_
        - 닫지 않은 파일 핸들 / 커넥션 풀
    """
    _global_cache[n] = list(range(1000))
    return len(_global_cache)


def clean_function(n: int) -> int:
    """지역 변수만 — 함수 끝나면 _gc_."""
    local_data = list(range(1000))
    return len(local_data) + n


def reset_leaky_state() -> None:
    """테스트 격리용."""
    _global_cache.clear()
