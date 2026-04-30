"""벤치마킹 유틸 — 단순 timing + 통계 (p50/p95/p99).

운영급 도구:
    - `pytest-benchmark` ── pytest 통합 + 통계 + 비교
    - `pyperf` ── 가장 정확 (warmup, GC 제어, 통계)

본 모듈은 _학습용_ 단순 헬퍼 — 의존성 X.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass
class BenchResult:
    name: str
    samples: list[float]  # 초 단위

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples)

    @property
    def median(self) -> float:
        return statistics.median(self.samples)

    def percentile(self, p: float) -> float:
        """p ∈ [0, 100]. 단순 nearest-rank — 운영은 numpy / pyperf 권장."""
        sorted_samples = sorted(self.samples)
        if not sorted_samples:
            return 0.0
        k = max(0, min(len(sorted_samples) - 1, int(p / 100 * len(sorted_samples))))
        return sorted_samples[k]

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)


def bench[T](name: str, fn: Callable[[], T], *, iterations: int = 100, warmup: int = 5) -> BenchResult:
    """함수 N번 실행 → BenchResult.

    warmup ── 첫 실행은 _캐시 / JIT / import_ 영향 → 결과에서 제외.
    """
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return BenchResult(name=name, samples=samples)


def faster(a: BenchResult, b: BenchResult) -> float:
    """`a` 가 `b` 보다 _몇 배 빠른지_ (p50 기준). > 1 = a 빠름."""
    if a.p50 == 0:
        return float("inf")
    return b.p50 / a.p50
