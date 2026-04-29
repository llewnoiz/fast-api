"""t03 — orjson: 빠르고 엄격한 JSON 직렬화.

비교:
    표준 json:     stdlib, 순수 Python, 느림, str 반환
    orjson:        Rust 작성, 표준 json 대비 _2~10배_ 빠름, bytes 반환
    Node:          내장 JSON.stringify (빠름)
    Java/Kotlin:   Jackson, kotlinx.serialization
    Go:            encoding/json (느림), goccy/go-json (빠름)
    PHP:           json_encode (내장)

orjson 의 강점:
    - **datetime / UUID / dataclass 자동 직렬화** (표준 json 은 default= 콜백 필요)
    - bytes 반환 — FastAPI 응답 본문에 바로 쓰기 좋음
    - 옵션 (indent, sort keys, naive utc) 으로 동작 커스터마이즈
    - FastAPI 의 `ORJSONResponse` 가 이걸 사용 → 04 단계에서 등장

이 모듈에서:
    1. 표준 json vs orjson — datetime 처리 차이
    2. 옵션 활용 (정렬, 들여쓰기, naive UTC)
    3. 성능 비교 (간단한 측정)
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from uuid import uuid4

import orjson

# ============================================================================
# 1) 표준 json 의 한계 — datetime / UUID 직렬화 못함
# ============================================================================


def demo_stdlib_pain_point() -> None:
    payload = {
        "id": uuid4(),
        "created_at": datetime.now(UTC),
        "name": "Alice",
    }

    try:
        json.dumps(payload)            # ❌ TypeError: not JSON serializable
    except TypeError as e:
        print("표준 json 실패:", e)

    # 우회: 매번 default 콜백 작성해야 함 — 보일러플레이트
    s = json.dumps(payload, default=str)
    print("표준 json + default=str:", s)


# ============================================================================
# 2) orjson — 그냥 됨
# ============================================================================


def demo_orjson_basic() -> None:
    payload = {
        "id": uuid4(),                  # ← 표준 json 은 못 함, orjson 은 자동
        "created_at": datetime.now(UTC),  # ← 표준 json 은 못 함, orjson 은 자동
        "tags": ["py", "rust"],         # set 은 기본 미지원 (OPT_PASSTHROUGH 필요)
        "name": "Alice",
    }

    # orjson.dumps 는 bytes 반환 — bytes 가 표준 (네트워크/파일 IO 자연스러움)
    raw: bytes = orjson.dumps(payload, option=orjson.OPT_NAIVE_UTC)
    print("orjson bytes:", raw)
    print("decode:", raw.decode())


# ============================================================================
# 3) 정렬 + 들여쓰기 옵션
# ============================================================================


def demo_orjson_options() -> None:
    payload = {"b": 2, "a": 1, "c": [3, 1, 2]}

    raw = orjson.dumps(
        payload,
        option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
    )
    print(raw.decode())


# ============================================================================
# 4) 성능 비교 (대략) — 환경마다 다르니 _감_ 만 잡기
# ============================================================================


def benchmark(n: int = 10_000) -> tuple[float, float]:
    payload = {f"key{i}": {"id": i, "name": f"user-{i}", "active": True} for i in range(50)}

    t0 = time.perf_counter()
    for _ in range(n):
        json.dumps(payload)
    t_stdlib = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(n):
        orjson.dumps(payload)
    t_orjson = time.perf_counter() - t0

    return t_stdlib, t_orjson


def main() -> None:
    print("=== 1) 표준 json 의 함정 ===")
    demo_stdlib_pain_point()

    print("\n=== 2) orjson 기본 ===")
    demo_orjson_basic()

    print("\n=== 3) 옵션 (정렬+들여쓰기) ===")
    demo_orjson_options()

    print("\n=== 4) 성능 비교 (1만 회 dumps) ===")
    t_std, t_orj = benchmark()
    print(f"  json (stdlib): {t_std * 1000:.1f} ms")
    print(f"  orjson       : {t_orj * 1000:.1f} ms")
    print(f"  배수         : {t_std / t_orj:.1f}×")


if __name__ == "__main__":
    main()
