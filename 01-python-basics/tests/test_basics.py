"""01단계 학습 코드의 핵심 함수/클래스에 대한 pytest 샘플.

JUnit 과 거의 같은 감각이지만:
- 클래스 없이 함수로 바로 작성 (관용)
- 단언은 `assert` 키워드 — pytest 가 실패 시 변수값을 친절히 출력
- fixture / parametrize 가 강력
"""

from __future__ import annotations

import pytest
from s01_types import find_user, stats
from s02_collections import (
    even_numbers,
    even_squares,
    flatten,
    label_signs,
    pairs_with_sum,
    squares_comprehension,
    squares_for_loop,
    squares_lazy,
    unique_lengths,
    word_lengths,
)
from s03_control_flow import InvalidScoreError, describe, grade, parse_score
from s04_functions import build_user, greet, paginate, sum_all
from s05_classes import Account, OrderStatus, Point, SavingsAccount, User, total_length
from s07_unpacking import (
    call_mixed_unpacking,
    call_with_dict_unpacking,
    call_with_list_unpacking,
    concat_lists,
    first_xy_and_label,
    insert_in_middle,
    merge_dicts,
    merge_dicts_in_place,
    merge_dicts_via_union,
    parse_csv_row,
    pick_via_dataclass,
    pick_via_index,
    pick_via_itemgetter,
    pick_via_match,
    split_first_middle_last,
    split_first_rest,
    split_head_last,
    split_pair,
    swap,
    union_sets,
)


# ---------- s01_types ----------
class TestTypes:
    def test_find_user_hit(self) -> None:
        assert find_user(1) == "Alice"

    def test_find_user_miss(self) -> None:
        assert find_user(999) is None  # `is None` 으로 비교

    def test_stats(self) -> None:
        result = stats([1, 2, 3, 4, 5])
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["avg"] == 3.0


# ---------- s02_collections (컴프리헨션) ----------
class TestComprehensions:
    def test_for_loop_and_comprehension_are_equivalent(self) -> None:
        """STEP 1: 같은 결과인지 확인 — 둘 다 0..n-1 의 제곱."""
        assert squares_for_loop(5) == squares_comprehension(5) == [0, 1, 4, 9, 16]

    def test_filter_only(self) -> None:
        # STEP 2: `if x % 2 == 0` 로 필터
        assert even_numbers(10) == [0, 2, 4, 6, 8]

    def test_filter_plus_map(self) -> None:
        # STEP 3: filter 뒤에 map(x*x)
        assert even_squares(10) == [0, 4, 16, 36, 64]

    def test_dict_comprehension(self) -> None:
        # STEP 4: dict 형태 — `{key: value for ...}`
        assert word_lengths(["foo", "bar", "hello"]) == {"foo": 3, "bar": 3, "hello": 5}

    def test_set_comprehension_dedupes(self) -> None:
        # STEP 4: set 은 자연스럽게 중복 제거
        assert unique_lengths(["a", "ab", "abc", "ab", "a"]) == {1, 2, 3}

    def test_nested_flatten(self) -> None:
        # STEP 5: 중첩 — 왼쪽 for 가 바깥, 오른쪽 for 가 안쪽
        assert flatten([[1, 2, 3], [4, 5], [6]]) == [1, 2, 3, 4, 5, 6]

    def test_pairs_with_sum(self) -> None:
        # STEP 5: 중첩 + filter
        result = pairs_with_sum([1, 2, 3, 4, 5], target=6)
        assert sorted(result) == [(1, 5), (2, 4)]  # (3,3) 은 같은 인덱스라 제외

    def test_label_signs_ternary_in_expression(self) -> None:
        # STEP 6: 표현식 자리의 if/else (filter 의 if 와 다름)
        assert label_signs([3, -1, 0, 5, -7]) == ["+", "-", "0", "+", "-"]

    def test_generator_is_lazy(self) -> None:
        """STEP 7: generator 는 next() 호출 전엔 계산되지 않음."""
        gen = squares_lazy(1_000_000)  # list 면 메모리 폭발, gen 은 안전
        # iterator 라서 list/tuple 이 _아님_
        assert not isinstance(gen, list)
        # 처음 5개만 꺼내도 잘 동작
        assert [next(gen) for _ in range(5)] == [0, 1, 4, 9, 16]


# ---------- s03_control_flow ----------
class TestControlFlow:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [(95, "A"), (85, "B"), (75, "C"), (50, "F"), (-1, "음수")],
    )
    def test_grade(self, score: int, expected: str) -> None:
        """parametrize: JUnit `@ParameterizedTest` 자리."""
        assert grade(score) == expected

    def test_describe_dispatch(self) -> None:
        assert describe(-3) == "음수 정수"
        assert describe(0) == "영"
        assert describe(7) == "양의 정수"
        assert describe([1, 2]) == "2-요소 리스트: (1, 2)"
        assert describe({"type": "user", "name": "A"}) == "user dict, name=A"

    def test_parse_score_ok(self) -> None:
        assert parse_score("50") == 50

    def test_parse_score_invalid_format(self) -> None:
        # `pytest.raises` 는 JUnit `assertThrows` 와 동일
        with pytest.raises(InvalidScoreError, match="파싱 실패"):
            parse_score("abc")

    def test_parse_score_out_of_range(self) -> None:
        with pytest.raises(InvalidScoreError, match="범위 밖"):
            parse_score("150")


# ---------- s04_functions ----------
class TestFunctions:
    def test_greet_default(self) -> None:
        assert greet("Alice") == "안녕, Alice"

    def test_greet_excited(self) -> None:
        assert greet("Bob", excited=True) == "안녕, Bob!"

    def test_sum_all(self) -> None:
        assert sum_all(1, 2, 3) == "합: 6"
        assert sum_all(10, 20, label="총합") == "총합: 30"

    def test_paginate_keyword_only(self) -> None:
        assert paginate("users") == "users?page=1&size=20"
        assert paginate("users", page=3, size=50) == "users?page=3&size=50"

    def test_paginate_rejects_positional(self) -> None:
        # page/size 는 키워드 전용 — 위치 인자로 주면 TypeError
        with pytest.raises(TypeError):
            paginate("users", 3, 50)  # type: ignore[misc]

    def test_build_user_sets_created_at(self) -> None:
        user = build_user(name="Alice")
        assert user["name"] == "Alice"
        assert "created_at" in user


# ---------- s05_classes ----------
class TestAccount:
    @pytest.fixture
    def account(self) -> Account:
        """fixture: 모든 테스트에서 깨끗한 인스턴스 제공. JUnit `@BeforeEach` 자리."""
        return Account("Alice", balance=100)

    def test_deposit(self, account: Account) -> None:
        account.deposit(50)
        assert account.balance == 150

    def test_negative_balance_rejected(self, account: Account) -> None:
        with pytest.raises(ValueError, match="음수"):
            account.balance = -10

    def test_factory(self) -> None:
        a = Account.from_str("Bob:500")
        assert a.owner == "Bob"
        assert a.balance == 500

    def test_static_method(self) -> None:
        assert Account.is_valid_owner("Al") is True
        assert Account.is_valid_owner("A") is False

    def test_savings_accrue(self) -> None:
        s = SavingsAccount("Carol", 1000, rate=0.1)
        s.accrue()
        assert s.balance == pytest.approx(1100)


class TestDataClass:
    def test_point_distance(self) -> None:
        assert Point(0, 0).distance_to(Point(3, 4)) == 5.0

    def test_user_validation(self) -> None:
        with pytest.raises(ValueError, match="음수 불가"):
            User(id=-1, name="X")

    def test_user_frozen(self) -> None:
        u = User(id=1, name="A")
        with pytest.raises(Exception):  # noqa: B017 — FrozenInstanceError 또는 AttributeError
            u.name = "B"  # type: ignore[misc]


class TestEnum:
    def test_terminal(self) -> None:
        assert OrderStatus.DELIVERED.is_terminal()
        assert OrderStatus.CANCELED.is_terminal()
        assert not OrderStatus.PENDING.is_terminal()


class TestProtocol:
    def test_total_length_duck_typed(self) -> None:
        items = ["abc", [1, 2, 3, 4], {"a": 1, "b": 2}]
        assert total_length(items) == 3 + 4 + 2


# ---------- s07_unpacking (구조 분해 & 결합) ----------
class TestUnpacking:
    # STEP 1
    def test_split_pair(self) -> None:
        assert split_pair((1, 2)) == (1, 2)

    def test_unpack_too_few_raises(self) -> None:
        # 좌변 변수 개수와 우변 길이가 안 맞으면 ValueError
        with pytest.raises(ValueError):
            a, b, c = (1, 2)  # noqa: F841 — 의도적 실패

    def test_parse_csv_row(self) -> None:
        assert parse_csv_row("Alice,a@x.com,admin") == ("Alice", "a@x.com", "admin")

    # STEP 2
    def test_split_first_rest(self) -> None:
        # JS: const [first, ...rest] = arr
        assert split_first_rest([1, 2, 3, 4]) == (1, [2, 3, 4])

    def test_split_head_last(self) -> None:
        assert split_head_last([1, 2, 3, 4]) == ([1, 2, 3], 4)

    def test_split_first_middle_last(self) -> None:
        # JS 에는 없는 _가운데에 rest_ 패턴
        assert split_first_middle_last([1, 2, 3, 4, 5]) == (1, [2, 3, 4], 5)

    def test_star_unpacking_with_min_size(self) -> None:
        # `*rest` 는 _0개_ 도 허용 (빈 list 가 됨)
        first, *rest = [42]
        assert first == 42
        assert rest == []

    # STEP 3
    def test_nested_unpacking(self) -> None:
        assert first_xy_and_label(((3.0, 4.0), "P")) == (3.0, 4.0, "P")

    def test_swap_idiom(self) -> None:
        assert swap("a", 1) == (1, "a")

    # STEP 4 — 호출 측 unpacking
    def test_call_with_list_unpacking(self) -> None:
        assert call_with_list_unpacking() == "안녕, Alice"

    def test_call_with_dict_unpacking(self) -> None:
        assert call_with_dict_unpacking() == "hi, Bob!"

    def test_call_mixed_unpacking(self) -> None:
        assert call_mixed_unpacking() == "yo, Carol!"

    # STEP 5 — PEP 448 spread
    def test_concat_lists(self) -> None:
        assert concat_lists([1, 2], [3, 4]) == [1, 2, 3, 4]

    def test_insert_in_middle(self) -> None:
        # `+` 로는 어색한 패턴, spread 가 깔끔
        assert insert_in_middle([1, 2], 99, [3, 4]) == [1, 2, 99, 3, 4]

    def test_union_sets(self) -> None:
        assert union_sets({1, 2}, {2, 3}) == {1, 2, 3}

    def test_merge_dicts_later_wins(self) -> None:
        # 키 충돌 시 _뒤가 이김_ (JS 와 동일)
        result = merge_dicts({"x": 1, "y": 2}, {"y": 99, "z": 3})
        assert result == {"x": 1, "y": 99, "z": 3}

    # STEP 6 — dict union 연산자
    def test_merge_via_union_returns_new_dict(self) -> None:
        a = {"x": 1}
        b = {"y": 2}
        result = merge_dicts_via_union(a, b)
        assert result == {"x": 1, "y": 2}
        # 원본은 변경 안 됨
        assert a == {"x": 1}
        assert b == {"y": 2}

    def test_merge_in_place_mutates(self) -> None:
        a = {"x": 1}
        merge_dicts_in_place(a, {"y": 2})
        assert a == {"x": 1, "y": 2}  # a 자체가 변경됨

    # STEP 7 — Node-style dict destructuring 의 4가지 대안
    @pytest.mark.parametrize(
        "picker",
        [pick_via_index, pick_via_itemgetter, pick_via_match, pick_via_dataclass],
    )
    def test_all_four_alternatives_equivalent(self, picker) -> None:  # type: ignore[no-untyped-def]
        """대안 4가지가 _같은 결과_ 를 내야 한다."""
        user = {"name": "Alice", "age": 30}
        assert picker(user) == ("Alice", 30)

    def test_match_alternative_rejects_missing_key(self) -> None:
        # 대안 3 (match) 는 키 누락 시 검증 실패 — 패턴 매칭의 장점
        with pytest.raises(ValueError, match="키 없음"):
            pick_via_match({"name": "Alice"})  # age 누락
