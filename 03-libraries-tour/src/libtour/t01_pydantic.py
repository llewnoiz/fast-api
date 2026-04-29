"""t01 — pydantic v2: 타입 기반 검증 + 직렬화.

비교 (가장 가까운 것 우선):
    TypeScript:      class-validator + class-transformer
                     또는 zod (zod 가 _가장_ 비슷한 모델)
    Kotlin:          data class + jakarta.validation (@NotBlank, @Min)
    Java + Spring:   @Valid + DTO + Lombok
    PHP:             Symfony Validator
    JS (zod 비유):   z.object({ name: z.string(), age: z.number().gt(0) })

pydantic 의 강점:
    - _런타임 검증_ (타입 힌트만 달면 검증 자동)
    - _자동 직렬화/역직렬화_ (model_dump / model_validate)
    - FastAPI 의 모든 요청/응답 검증의 기반
    - 에러 메시지 풍부 (어느 필드, 어떤 규칙 위반인지 정확히)

이 모듈에서 보여주는 것:
    1. 기본 모델 + 자동 타입 변환
    2. 필드 제약 (Field)
    3. 중첩 모델
    4. 별칭 (alias) — JSON snake_case ↔ Python camel_case
    5. model_config 로 동작 커스터마이즈
    6. 검증 에러 처리
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, field_validator
from pydantic_core.core_schema import ValidationInfo

# ============================================================================
# 1) 기본 모델 — TS 의 zod 와 가장 가까움
# ============================================================================
#
# zod 비교:
#   const User = z.object({
#       id: z.number(),
#       name: z.string(),
#       active: z.boolean().default(true),
#   })
#
# pydantic:
#   class User(BaseModel):
#       id: int
#       name: str
#       active: bool = True
# ============================================================================


class User(BaseModel):
    id: int
    name: str
    active: bool = True


def demo_basic() -> None:
    # 자동 타입 변환 (느슨) — "1" 도 1 로 받아줌
    u = User(id=1, name="Alice")
    print("기본:", u)
    print("dict:", u.model_dump())     # → JSON 직렬화 가능한 dict
    print("json:", u.model_dump_json())  # → 문자열


# ============================================================================
# 2) 필드 제약 — Kotlin/Java 의 @Min/@NotBlank 자리
# ============================================================================
#
# Kotlin + jakarta.validation:
#   data class Order(
#       @field:Min(1) val quantity: Int,
#       @field:NotBlank val sku: String,
#   )
#
# pydantic:
#   class Order(BaseModel):
#       quantity: int = Field(gt=0)             # > 0
#       sku: str = Field(min_length=1, max_length=20)
# ============================================================================


class Order(BaseModel):
    quantity: int = Field(gt=0, le=1000, description="1 이상 1000 이하")
    sku: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z0-9-]+$")
    price: float = Field(ge=0)


def demo_field_constraints() -> None:
    try:
        Order(quantity=0, sku="abc", price=10)   # quantity gt=0 위반, sku 패턴 위반
    except ValidationError as e:
        # 에러 메시지가 _필드별로_ 풍부 — Spring 의 BindingResult 이상
        print("검증 에러 개수:", len(e.errors()))
        for err in e.errors():
            print(f"  - {err['loc']}: {err['msg']}")


# ============================================================================
# 3) 중첩 모델 — TypeScript 의 nested interface 자리
# ============================================================================


class Address(BaseModel):
    city: str
    country: str = "KR"


class Customer(BaseModel):
    name: str
    email: EmailStr                  # 이메일 형식 자동 검증 (pydantic[email] extra 필요할 수도)
    address: Address                 # 중첩 — dict 로 들어와도 자동 변환
    created_at: datetime = Field(default_factory=datetime.now)


def demo_nested() -> None:
    raw = {
        "name": "Alice",
        "email": "a@example.com",
        "address": {"city": "Seoul"},   # country 는 기본값 사용
    }
    c = Customer.model_validate(raw)
    print("중첩 모델:", c)
    print("address.city:", c.address.city)


# ============================================================================
# 4) 별칭 (alias) — JSON snake_case ↔ Python 친화 이름
# ============================================================================
#
# 외부 API 가 user_name 으로 보내고 우리 코드는 username 을 쓰고 싶을 때.
# Spring `@JsonProperty`, Kotlin `@SerialName`, TS class-transformer `@Expose` 자리.
# ============================================================================


class ApiResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="requestId")   # 외부는 camelCase, 우리는 snake_case
    items: list[str]


def demo_alias() -> None:
    # 외부 JSON 그대로 검증 (camelCase 키)
    r = ApiResponse.model_validate({"requestId": "abc-123", "items": ["a", "b"]})
    print("별칭 입력:", r)
    print("dump (alias 유지):", r.model_dump(by_alias=True))


# ============================================================================
# 5) 커스텀 validator — Spring `@AssertTrue` / Kotlin `init { require(...) }`
# ============================================================================


class Range(BaseModel):
    start: int
    end: int

    @field_validator("end")
    @classmethod
    def end_must_exceed_start(cls, v: int, info: ValidationInfo) -> int:
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("end must be > start")
        return v


def demo_custom_validator() -> None:
    try:
        Range(start=10, end=5)
    except ValidationError as e:
        print("커스텀 검증:", e.errors()[0]["msg"])


def main() -> None:
    print("=== 1) 기본 모델 ===")
    demo_basic()

    print("\n=== 2) 필드 제약 ===")
    demo_field_constraints()

    print("\n=== 3) 중첩 모델 ===")
    demo_nested()

    print("\n=== 4) 별칭 (alias) ===")
    demo_alias()

    print("\n=== 5) 커스텀 validator ===")
    demo_custom_validator()


if __name__ == "__main__":
    main()
