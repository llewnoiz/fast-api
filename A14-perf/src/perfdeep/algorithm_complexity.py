"""알고리즘 복잡도 — _운영급_ 측정으로 O(n²) vs O(n) 차이 _체감_.

원칙:
    "성능은 _측정_ 한 만큼만 안다. 복잡도 _직관_ 으로 결정 X."

동시에 — _복잡도 분석_ 도 무시 X. 큰 입력에서 _측정 안 해도_ 망함.
"""

from __future__ import annotations


# ── 검색 ──
def linear_search(items: list[int], target: int) -> int:
    """O(n)."""
    for i, item in enumerate(items):
        if item == target:
            return i
    return -1


def binary_search(sorted_items: list[int], target: int) -> int:
    """O(log n) — 정렬 _전제_. 정렬 비용 (O(n log n)) 고려해야."""
    lo, hi = 0, len(sorted_items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_items[mid] == target:
            return mid
        if sorted_items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


# ── 중복 검사 ──
def has_duplicate_quadratic(items: list[int]) -> bool:
    """O(n²) — 모든 쌍 비교."""
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            if items[i] == items[j]:
                return True
    return False


def has_duplicate_set(items: list[int]) -> bool:
    """O(n) — set 사용. 메모리 _O(n)_ 추가 (트레이드오프)."""
    seen: set[int] = set()
    for item in items:
        if item in seen:
            return True
        seen.add(item)
    return False


# ── 빈도 카운트 ──
def count_naive(items: list[str]) -> dict[str, int]:
    """O(n) but key not in dict _두 번 lookup_."""
    counts: dict[str, int] = {}
    for item in items:
        if item in counts:
            counts[item] += 1
        else:
            counts[item] = 1
    return counts


def count_dict_get(items: list[str]) -> dict[str, int]:
    """`dict.get(k, 0)` ── lookup _한 번_ + default. 더 빠름 + 가독성 ↑."""
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


def count_collections_counter(items: list[str]) -> dict[str, int]:
    """C 구현 ── 보통 _가장 빠름_. import 비용 (한 번)만."""
    from collections import Counter  # noqa: PLC0415

    return dict(Counter(items))


# ── 누적 합 ──
def cumulative_quadratic(nums: list[int]) -> list[int]:
    """O(n²) ── 매번 sum() 다시 계산."""
    return [sum(nums[: i + 1]) for i in range(len(nums))]


def cumulative_linear(nums: list[int]) -> list[int]:
    """O(n) ── 한 번의 누적."""
    result = []
    total = 0
    for n in nums:
        total += n
        result.append(total)
    return result
