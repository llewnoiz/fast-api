"""Schema Registry — 메시지 스키마 _진화_ 와 _호환성_ 관리.

배경:
    Kafka / Pulsar / RabbitMQ 같은 broker 는 _바이트만_ 전달. 메시지 _구조_ 는 producer 와
    consumer 가 _합의_ 해야 함. 코드가 분산되면 _스키마 변경_ 이 곧 _배포 순서 의존성_.

해결:
    - _Schema Registry_ (Confluent / Apicurio / AWS Glue) ── 스키마 _중앙 보관_ + _버전_ + _호환성 정책_.
    - 메시지에 schema ID 를 붙여 보냄 (`magic byte + schema_id + payload`).
    - consumer 는 ID 로 registry 에서 스키마 조회 → 안전 deserialize.

**호환성 정책 4종**:

| 정책 | 의미 | 안전한 변경 |
|---|---|---|
| **BACKWARD** | 새 스키마로 _옛 데이터_ 읽기 가능 | 필드 추가 (default), 필드 삭제 |
| **FORWARD** | 옛 스키마로 _새 데이터_ 읽기 가능 | 필드 추가, 필드 삭제 (default) |
| **FULL** | 양방향 | 필드 추가 (default), 필드 삭제 (default) |
| **NONE** | 검증 안 함 | _아무거나_ ── 위험 |

기본은 보통 **BACKWARD** ── consumer 를 _먼저_ 업데이트, producer 를 _나중_ 에. (consumer 는 옛/신 둘 다 처리 가능해야).

**포맷 비교**:

| 포맷 | 장점 | 단점 |
|---|---|---|
| **JSON Schema** | 사람이 읽기 좋음, 디버깅 쉬움 | 큰 페이로드, 느린 직렬화 |
| **Avro** | 작고 빠름, _이진_ , 스키마 진화 우수 | _스키마 없으면 못 읽음_ |
| **Protobuf** | 가장 빠름, gRPC 표준, 다국어 stub | 스키마 진화 _Avro 보다 까다로움_ (옵셔널/required) |

본 모듈:
    - JSON Schema 기반 _최소_ registry (in-memory)
    - 호환성 검사 (BACKWARD / FORWARD)
    - 메시지 직렬화/역직렬화 with schema ID

비교:
    Confluent Schema Registry — Avro/JSON/Protobuf 다 지원, Kafka 표준
    Apicurio — 오픈소스 대체, REST API 호환
    AWS Glue Schema Registry — AWS 매니지드
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import jsonschema


class CompatibilityMode(StrEnum):
    BACKWARD = "BACKWARD"
    FORWARD = "FORWARD"
    FULL = "FULL"
    NONE = "NONE"


class SchemaCompatibilityError(Exception):
    """새 스키마가 호환성 정책을 위반."""


@dataclass
class SchemaVersion:
    id: int
    subject: str
    version: int
    schema: dict[str, Any]


@dataclass
class SchemaRegistry:
    """학습용 인메모리. 운영: Confluent / Apicurio / Glue."""

    _by_subject: dict[str, list[SchemaVersion]] = field(default_factory=dict)
    _next_id: int = 1
    compatibility: CompatibilityMode = CompatibilityMode.BACKWARD

    def register(self, subject: str, schema: dict[str, Any]) -> SchemaVersion:
        existing = self._by_subject.get(subject, [])
        if existing:
            latest = existing[-1]
            self._check_compatibility(latest.schema, schema)
            version = latest.version + 1
        else:
            version = 1

        sv = SchemaVersion(id=self._next_id, subject=subject, version=version, schema=schema)
        self._next_id += 1
        self._by_subject.setdefault(subject, []).append(sv)
        return sv

    def latest(self, subject: str) -> SchemaVersion:
        versions = self._by_subject.get(subject)
        if not versions:
            raise KeyError(f"unknown subject: {subject}")
        return versions[-1]

    def get(self, schema_id: int) -> SchemaVersion:
        for versions in self._by_subject.values():
            for v in versions:
                if v.id == schema_id:
                    return v
        raise KeyError(f"unknown schema id: {schema_id}")

    def validate_message(self, schema_id: int, message: dict[str, Any]) -> None:
        sv = self.get(schema_id)
        jsonschema.validate(message, sv.schema)

    # ── 호환성 검사 (학습용 단순화) ─────────────────────────────────
    # 실제 Confluent 알고리즘은 _필드 단위_ 로 정밀 비교. 본 구현은 _필드 집합_ 차이만.

    def _check_compatibility(
        self, old: dict[str, Any], new: dict[str, Any]
    ) -> None:
        if self.compatibility == CompatibilityMode.NONE:
            return

        old_required = set(old.get("required", []))
        new_required = set(new.get("required", []))
        old_props = set((old.get("properties") or {}).keys())
        new_props = set((new.get("properties") or {}).keys())

        if self.compatibility in (CompatibilityMode.BACKWARD, CompatibilityMode.FULL):
            # 새 스키마로 _옛 데이터_ 읽기 → 옛 데이터에 없는 _required 필드 추가_ 는 위반
            added_required = new_required - old_required
            removed_props = old_props - new_props
            if added_required & set(new_props):
                # default 가 없는 새 required 가 추가되면 옛 데이터 검증 실패
                violating = {
                    f for f in added_required
                    if "default" not in (new.get("properties", {}).get(f) or {})
                }
                if violating:
                    raise SchemaCompatibilityError(
                        f"BACKWARD violation — required without default added: {violating}"
                    )
            if removed_props:
                raise SchemaCompatibilityError(
                    f"BACKWARD violation — properties removed: {removed_props}"
                )

        if self.compatibility in (CompatibilityMode.FORWARD, CompatibilityMode.FULL):
            # 옛 스키마로 _새 데이터_ 읽기 → 옛 required 가 새 스키마에서 사라지면 위반
            removed_required = old_required - new_required
            if removed_required:
                raise SchemaCompatibilityError(
                    f"FORWARD violation — required removed: {removed_required}"
                )
