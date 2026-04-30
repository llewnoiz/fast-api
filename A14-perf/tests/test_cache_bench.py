"""캐시 효과 측정."""

from __future__ import annotations

from perfdeep.bench_utils import bench, faster
from perfdeep.cache_bench import (
    ExpensiveReport,
    fib_no_cache,
    fib_with_cache,
)


def test_fib_results_match_for_small_n() -> None:
    for n in range(20):
        assert fib_no_cache(n) == fib_with_cache(n)


def test_cached_fib_faster_at_large_n() -> None:
    """fib(30) 은 캐시 없으면 ~수백만 호출, 캐시면 _O(n)_.

    test 안전을 위해 fib_no_cache 는 _작은 n_ 만 측정.
    """
    # 캐시 _재호출_ 가 0에 가까울 정도로 빠른지
    cached = bench("cached", lambda: fib_with_cache(25), iterations=100, warmup=5)
    uncached = bench("naive", lambda: fib_no_cache(20), iterations=20, warmup=2)
    # n 작아도 무캐시가 훨씬 느림
    assert faster(cached, uncached) > 5


def test_cached_property_caches_per_instance() -> None:
    r = ExpensiveReport(data=[1, 2, 3, 4])
    first = r.expensive_total
    second = r.expensive_total
    assert first == second == 1 + 4 + 9 + 16
    # 두 번째 접근부턴 _instance dict_ 에 hit
    assert "expensive_total" in r.__dict__
