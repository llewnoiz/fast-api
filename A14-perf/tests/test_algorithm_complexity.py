"""알고리즘 복잡도 — _측정_ 으로 차이 확인."""

from __future__ import annotations

import random

from perfdeep.algorithm_complexity import (
    binary_search,
    count_collections_counter,
    count_dict_get,
    count_naive,
    cumulative_linear,
    cumulative_quadratic,
    has_duplicate_quadratic,
    has_duplicate_set,
    linear_search,
)
from perfdeep.bench_utils import bench, faster


def test_search_correctness() -> None:
    items = [1, 3, 5, 7, 9, 11, 13]
    assert linear_search(items, 7) == 3
    assert binary_search(items, 7) == 3
    assert linear_search(items, 100) == -1
    assert binary_search(items, 100) == -1


def test_binary_faster_than_linear_on_large() -> None:
    """sorted 1만 → binary 가 명확히 빠름."""
    items = list(range(10_000))

    linear_result = bench(
        "linear", lambda: linear_search(items, 9999), iterations=200, warmup=10
    )
    binary_result = bench(
        "binary", lambda: binary_search(items, 9999), iterations=200, warmup=10
    )
    # 적어도 5배 빠르길 기대 (현실적 lower bound)
    assert faster(binary_result, linear_result) > 5


def test_set_dedupe_faster_than_quadratic() -> None:
    rng = random.Random(42)
    items = [rng.randint(0, 10000) for _ in range(500)]

    qua = bench("quadratic", lambda: has_duplicate_quadratic(items), iterations=20, warmup=2)
    set_ = bench("set", lambda: has_duplicate_set(items), iterations=20, warmup=2)
    # set 이 _훨씬_ 빠름
    assert faster(set_, qua) > 10


def test_count_methods_same_result() -> None:
    words = ["a", "b", "a", "c", "b", "a"]
    naive = count_naive(words)
    via_get = count_dict_get(words)
    via_counter = count_collections_counter(words)
    assert naive == via_get == via_counter == {"a": 3, "b": 2, "c": 1}


def test_cumulative_methods_match() -> None:
    nums = list(range(20))
    assert cumulative_linear(nums) == cumulative_quadratic(nums)


def test_cumulative_linear_faster_than_quadratic() -> None:
    nums = list(range(500))
    qua = bench(
        "qua", lambda: cumulative_quadratic(nums), iterations=20, warmup=2
    )
    lin = bench("lin", lambda: cumulative_linear(nums), iterations=20, warmup=2)
    assert faster(lin, qua) > 10
