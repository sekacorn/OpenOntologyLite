"""Runtime entity and action contract tests."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from open_ontology_lite import (
    RuntimeLimits,
    check_action_contract,
    load_ontology,
    validate_entity_instance,
)
from open_ontology_lite.models import ActionDef, EntityDef, PropertyDef

ROOT = Path(__file__).parents[1]


def _runtime_ontology():  # type: ignore[no-untyped-def]
    ontology = load_ontology(ROOT / "examples" / "customer_support.yaml")
    customer = ontology.entities["Customer"]
    customer_properties = dict(customer.properties)
    customer_properties["customer_id"] = customer_properties["customer_id"].model_copy(
        update={"aliases": ("id",)}
    )
    entities = dict(ontology.entities)
    entities["Customer"] = customer.model_copy(
        update={"aliases": ("Client",), "properties": customer_properties}
    )
    entities["RuntimeData"] = EntityDef(
        properties={
            "name": PropertyDef(
                type="string",
                required=True,
                pattern=r"[A-Z][a-z]+",
                min_length=2,
                max_length=12,
            ),
            "age": PropertyDef(type="integer", minimum=0, maximum=120),
            "score": PropertyDef(type="number", minimum=0, maximum=1),
            "ratio": PropertyDef(type="number", maximum=Decimal("0.1")),
            "amount": PropertyDef(type="decimal", minimum=0),
            "active": PropertyDef(type="boolean"),
            "day": PropertyDef(type="date"),
            "moment": PropertyDef(type="datetime"),
            "identifier": PropertyDef(type="uuid"),
            "tags": PropertyDef(
                type="array",
                items_schema=PropertyDef(type="integer"),
                min_length=1,
                max_length=3,
            ),
            "profile": PropertyDef(
                type="object",
                properties={"label": PropertyDef(type="string", required=True)},
            ),
            "payload": PropertyDef(type="object"),
            "customer": PropertyDef(type="reference", target="Customer"),
            "optional": PropertyDef(type="string", nullable=True),
        }
    )
    actions = tuple(
        action.model_copy(
            update={
                "aliases": ("refund",),
                "risk": "high",
                "review_required": True,
                "escalation": ("manager_review",),
                "expected_audit_events": ("refund_checked",),
            }
        )
        if action.name == "issue_refund"
        else action
        for action in ontology.actions
    )
    actions += (
        ActionDef(
            name="echo",
            subject="RuntimeData",
            inputs={"value": PropertyDef(type="string", required=True)},
            output=PropertyDef(type="string"),
            audit_required=False,
        ),
    )
    return ontology.model_copy(update={"entities": entities, "actions": actions})


def _codes(result: object) -> set[str]:
    return {issue.code for issue in result.issues}  # type: ignore[attr-defined]


def test_entity_validation_defaults_aliases_and_input_immutability() -> None:
    ontology = _runtime_ontology()
    value = {"id": "C-1042"}
    before = deepcopy(value)
    result = validate_entity_instance(ontology, entity_type="Client", value=value)
    assert result.valid
    assert result.entity_type == "Customer"
    assert result.aliases_required
    assert result.defaults_required
    assert result.normalized_value == {
        "account_status": "active",
        "customer_id": "C-1042",
    }
    assert value == before
    assert result.to_dict()["valid"] is True


def test_entity_unknown_collision_and_strict_modes() -> None:
    ontology = _runtime_ontology()
    unknown = validate_entity_instance(ontology, entity_type="Missing", value={})
    assert _codes(unknown) == {"UNKNOWN_ENTITY_TYPE"}

    collision = validate_entity_instance(
        ontology,
        entity_type="Customer",
        value={"customer_id": "C-1", "id": "C-2"},
    )
    assert "ALIAS_COLLISION" in _codes(collision)

    strict = validate_entity_instance(
        ontology,
        entity_type="Customer",
        value={"customer_id": "C-1", "extra": "secret"},
    )
    relaxed = validate_entity_instance(
        ontology,
        entity_type="Customer",
        value={"customer_id": "C-1", "extra": "secret"},
        strict=False,
    )
    assert not strict.valid
    assert relaxed.valid
    assert relaxed.issues[0].context == {"name_length": 5}


def test_entity_primitive_formats_nested_values_and_references() -> None:
    ontology = _runtime_ontology()
    result = validate_entity_instance(
        ontology,
        entity_type="RuntimeData",
        value={
            "name": "Alice",
            "age": 42,
            "score": 0.5,
            "ratio": 0.1,
            "amount": "10.25",
            "active": True,
            "day": "2026-01-02",
            "moment": "2026-01-02T03:04:05Z",
            "identifier": "12345678-1234-5678-1234-567812345678",
            "tags": [1, 2],
            "profile": {"label": "primary"},
            "payload": {"nested": [1, True, "value"]},
            "customer": "C-1",
            "optional": None,
        },
    )
    assert result.valid
    assert result.normalized_value is not None
    assert result.normalized_value["amount"] == Decimal("10.25")
    assert result.to_dict()["normalized_value"]["amount"] == "10.25"
    assert result.normalized_value["payload"] == {"nested": [1, True, "value"]}

    expanded = validate_entity_instance(
        ontology,
        entity_type="RuntimeData",
        value={"name": "Alice", "customer": {"customer_id": "C-1"}},
    )
    assert expanded.valid


def test_entity_rejects_invalid_types_formats_and_constraints() -> None:
    ontology = _runtime_ontology()
    result = validate_entity_instance(
        ontology,
        entity_type="RuntimeData",
        value={
            "name": "x",
            "age": 121,
            "score": float("inf"),
            "amount": 10.25,
            "active": 1,
            "day": "not-a-date",
            "moment": "not-a-datetime",
            "identifier": "not-a-uuid",
            "tags": ["wrong", 2, 3, 4],
            "profile": {},
            "customer": "",
            "optional": 1,
        },
    )
    assert {
        "MAX_LENGTH",
        "MAXIMUM",
        "MIN_LENGTH",
        "PATTERN_MISMATCH",
        "REQUIRED_PROPERTY_MISSING",
        "TYPE_MISMATCH",
        "UNSAFE_DECIMAL_FLOAT",
        "INVALID_DATE",
        "INVALID_DATETIME",
        "INVALID_UUID",
        "EMPTY_REFERENCE",
    } <= _codes(result)

    numeric_string = validate_entity_instance(
        ontology,
        entity_type="RuntimeData",
        value={"name": "Alice", "score": "0.5"},
    )
    assert "TYPE_MISMATCH" in _codes(numeric_string)


def test_entity_runtime_limits_and_sanitized_diagnostics() -> None:
    ontology = _runtime_ontology()
    result = validate_entity_instance(
        ontology,
        entity_type="RuntimeData",
        value={"name": "A" * 20, "tags": list(range(5))},
        limits=RuntimeLimits(
            max_collection_items=3,
            max_string_length=5,
            max_pattern_input=4,
            max_issues=1,
        ),
    )
    assert "DIAGNOSTIC_LIMIT_REACHED" in _codes(result)
    serialized = str(result.to_dict())
    assert "AAAAAA" not in serialized

    aggregate = validate_entity_instance(
        ontology,
        entity_type="RuntimeData",
        value={"name": "Alice", "payload": {"a": [1, 2, 3]}},
        limits=RuntimeLimits(max_total_nodes=4),
    )
    assert "TOTAL_NODE_LIMIT_EXCEEDED" in _codes(aggregate)


def test_entity_invalid_pattern_reference_and_default() -> None:
    ontology = _runtime_ontology()
    entities = dict(ontology.entities)
    entities["Unsafe"] = EntityDef(
        properties={
            "pattern": PropertyDef(type="string", pattern=r"(a+)+"),
            "missing_ref": PropertyDef(type="reference", target="Missing"),
            "bad_default": PropertyDef(type="integer", required=True, default="wrong"),
        }
    )
    changed = ontology.model_copy(update={"entities": entities})
    result = validate_entity_instance(
        changed,
        entity_type="Unsafe",
        value={"pattern": "aaaa", "missing_ref": {"id": "x"}},
    )
    assert {"UNSAFE_PATTERN", "UNKNOWN_REFERENCE_TARGET", "INVALID_DEFAULT"} <= _codes(result)


def test_action_contract_status_permissions_preconditions_and_metadata() -> None:
    ontology = _runtime_ontology()
    missing = check_action_contract(
        ontology,
        action="refund",
        inputs={"reason": "duplicate", "amount": "12.00"},
    )
    assert missing.status == "unsatisfied"
    assert missing.missing_permissions == ("billing.refund",)
    assert missing.risk == "high"
    assert missing.review_required
    assert missing.escalation_expectations == ("manager_review",)
    assert missing.expected_audit_events == ("refund_checked",)
    assert missing.validated_inputs is not None
    assert missing.validated_inputs["amount"] == Decimal("12.00")

    checked = check_action_contract(
        ontology,
        action="issue_refund",
        inputs={"reason": "duplicate", "amount": "12.00"},
        actor_permissions=["billing.refund"],
        context={"manager_approved": False},
    )
    assert checked.status == "indeterminate"
    assert checked.valid is False
    assert len(checked.unresolved_preconditions) == 2
    assert "PRECONDITION_UNRESOLVED" in _codes(checked)
    assert checked.to_dict()["validated_inputs"]["amount"] == "12.00"


def test_action_contract_satisfied_output_and_failure_cases() -> None:
    ontology = _runtime_ontology()
    satisfied = check_action_contract(
        ontology,
        action="echo",
        inputs={"value": "hello"},
        output="world",
    )
    assert satisfied.status == "satisfied"
    assert satisfied.valid
    assert satisfied.validated_output == "world"

    invalid_output = check_action_contract(
        ontology,
        action="echo",
        inputs={"value": "hello"},
        output=1,
    )
    assert invalid_output.status == "unsatisfied"

    unknown = check_action_contract(ontology, action="missing", inputs={})
    assert unknown.status == "unsatisfied"
    assert _codes(unknown) == {"UNKNOWN_ACTION"}

    undeclared_output = check_action_contract(
        ontology,
        action="create_ticket",
        inputs={"customer_id": "C-1", "description": "help"},
        actor_permissions=["support.ticket.create"],
        output={"ticket_id": "T-1"},
    )
    assert undeclared_output.status == "indeterminate"
    assert "OUTPUT_CONTRACT_UNDECLARED" in _codes(undeclared_output)
