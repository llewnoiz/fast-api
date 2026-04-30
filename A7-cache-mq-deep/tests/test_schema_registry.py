"""Schema Registry — 등록 / 호환성 검사 / 검증."""

from __future__ import annotations

import jsonschema
import pytest
from cachemqdeep.schema_registry import (
    CompatibilityMode,
    SchemaCompatibilityError,
    SchemaRegistry,
)


def test_register_first_version() -> None:
    reg = SchemaRegistry()
    sv = reg.register(
        "OrderCreated",
        {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    )
    assert sv.version == 1


def test_backward_compatible_add_optional_field() -> None:
    reg = SchemaRegistry(compatibility=CompatibilityMode.BACKWARD)
    reg.register(
        "OrderCreated",
        {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    )
    # _옵셔널_ 필드 추가 — BACKWARD OK
    sv2 = reg.register(
        "OrderCreated",
        {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": ["order_id"],
        },
    )
    assert sv2.version == 2


def test_backward_violation_when_required_added_without_default() -> None:
    reg = SchemaRegistry(compatibility=CompatibilityMode.BACKWARD)
    reg.register(
        "OrderCreated",
        {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    )
    with pytest.raises(SchemaCompatibilityError):
        reg.register(
            "OrderCreated",
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "shipping": {"type": "string"},
                },
                "required": ["order_id", "shipping"],
            },
        )


def test_validate_message_against_schema() -> None:
    reg = SchemaRegistry()
    sv = reg.register(
        "OrderCreated",
        {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    )
    reg.validate_message(sv.id, {"order_id": 1})
    with pytest.raises(jsonschema.ValidationError):
        reg.validate_message(sv.id, {"order_id": "wrong-type"})


def test_unknown_subject_raises() -> None:
    reg = SchemaRegistry()
    with pytest.raises(KeyError):
        reg.latest("nope")
