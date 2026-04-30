"""bench 헬퍼 단위 테스트."""

from __future__ import annotations

from perfdeep.bench_utils import BenchResult, bench, faster


def test_bench_runs_iterations() -> None:
    counter = {"n": 0}

    def increment() -> None:
        counter["n"] += 1

    result = bench("inc", increment, iterations=10, warmup=2)
    # warmup(2) + iterations(10) = 12
    assert counter["n"] == 12
    assert len(result.samples) == 10


def test_bench_result_percentiles() -> None:
    samples = [0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.010]
    r = BenchResult(name="x", samples=samples)
    assert r.p50 == 0.006
    assert r.p95 == 0.010


def test_faster_returns_ratio() -> None:
    fast = BenchResult(name="fast", samples=[0.001] * 5)
    slow = BenchResult(name="slow", samples=[0.010] * 5)
    ratio = faster(fast, slow)
    assert ratio == 10.0


def test_bench_result_mean_median() -> None:
    r = BenchResult(name="x", samples=[1.0, 2.0, 3.0])
    assert r.mean == 2.0
    assert r.median == 2.0
