"""t04 — jsonpath-ng + 깊은 병합(deep merge).

비교:
    JS:        lodash.get / lodash.merge / JSONPath-Plus
    Java:      Jayway JsonPath (`com.jayway.jsonpath`)
    Kotlin:    Jackson JsonPointer 또는 Jayway
    SQL:       PostgreSQL `->`, `->>`, `jsonb_path_query`

JSONPath 는 _XPath 의 JSON 버전_:
    $.users[*].name           → 모든 user 의 name
    $.orders[?(@.amount>100)] → amount > 100 인 order
    $..email                  → 어디든 있는 email 키

이 모듈에서:
    1. 단일 값 get
    2. 컬렉션 쿼리 (필터)
    3. 깊은 병합(deep merge) — `{**a, **b}` 의 _얕은_ 한계 보완

`{**a, **b}` 는 1단계만 병합하지만 — `{"meta": {...}}` 같이 중첩되면 _덮어쓰기_.
실무에선 환경별 설정 병합 (default + local + secret) 시 deep merge 가 필요.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from jsonpath_ng.ext import parse as jp_parse

# ============================================================================
# 1) 단일/다중 값 쿼리
# ============================================================================
#
# JS lodash:    _.get(data, "users[0].name")
# Java Jayway:  JsonPath.read(json, "$.users[0].name")
# jsonpath-ng:  parse("$.users[0].name").find(data) → [Match] 리스트
# ============================================================================


def query_one(data: dict[str, Any], expr: str) -> Any:
    """첫 매치만 반환. 없으면 None."""
    matches = jp_parse(expr).find(data)
    return matches[0].value if matches else None


def query_all(data: dict[str, Any], expr: str) -> list[Any]:
    """모든 매치 반환."""
    return [m.value for m in jp_parse(expr).find(data)]


# ============================================================================
# 2) 깊은 병합 — `{**a, **b}` 의 한계 보완
# ============================================================================
#
# 얕은 병합 (PEP 448, Python 3.9+ 의 a | b):
#   a = {"meta": {"x": 1}}
#   b = {"meta": {"y": 2}}
#   {**a, **b}                → {"meta": {"y": 2}}      ← x 잃어버림
#
# 깊은 병합 (재귀):
#   deep_merge(a, b)          → {"meta": {"x": 1, "y": 2}}  ✅
#
# JS lodash _.merge 와 동일 의미. 환경별 설정 병합 (default + override) 핵심 도구.
# ============================================================================


def deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """b 가 a 에 _재귀적으로_ 덮어씌움. 원본 수정 X (deepcopy).

    충돌 규칙:
        - 둘 다 dict → 재귀 병합
        - 그 외 → b 가 이김 (얕은 병합과 동일)
    """
    result = deepcopy(a)
    for key, b_val in b.items():
        if key in result and isinstance(result[key], dict) and isinstance(b_val, dict):
            result[key] = deep_merge(result[key], b_val)
        else:
            result[key] = deepcopy(b_val)
    return result


# ============================================================================
# 3) 데모용 샘플 데이터
# ============================================================================


SAMPLE = {
    "users": [
        {"id": 1, "name": "Alice", "email": "a@x.com", "active": True},
        {"id": 2, "name": "Bob",   "email": "b@x.com", "active": False},
        {"id": 3, "name": "Carol", "email": "c@x.com", "active": True},
    ],
    "meta": {
        "page": 1,
        "size": 20,
        "filters": {"status": "active"},
    },
}


def main() -> None:
    print("=== 1) 단일 값 쿼리 ===")
    print("first user name:", query_one(SAMPLE, "$.users[0].name"))
    print("meta.page       :", query_one(SAMPLE, "$.meta.page"))

    print("\n=== 2) 컬렉션 쿼리 ===")
    print("모든 name      :", query_all(SAMPLE, "$.users[*].name"))
    print("active=True 의 name:", query_all(SAMPLE, "$.users[?(@.active==true)].name"))
    print("어디든 email   :", query_all(SAMPLE, "$..email"))

    print("\n=== 3) 깊은 병합 ===")
    default_cfg = {
        "db": {"host": "localhost", "port": 5432, "pool": {"min": 1, "max": 10}},
        "cache": {"ttl": 60},
    }
    override = {
        "db": {"host": "prod.db", "pool": {"max": 50}},   # min 은 그대로 유지되어야 함
        "cache": {"ttl": 300},
    }

    shallow = {**default_cfg, **override}                 # ❌ db.port, db.pool.min 사라짐
    print("얕은 (안 좋음):", shallow)

    deep = deep_merge(default_cfg, override)              # ✅
    print("깊은 (정답):  ", deep)


if __name__ == "__main__":
    main()
