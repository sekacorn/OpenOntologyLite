"""Neutral contract and migration consistency tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from open_ontology_lite import (
    action_input_schema,
    action_output_schema,
    build_migration_plan,
    check_action_contract,
    generate_audit_context,
    generate_benchmark_fixture,
    generate_meter_attribution,
    generate_policy_context,
    generate_rag_metadata,
    generate_tool_contract,
    load_ontology,
    ontology_digest,
)
from open_ontology_lite.diffing import diff_ontologies
from open_ontology_lite.migrations import migration_plan_json, migration_plan_markdown
from open_ontology_lite.models import Ontology, PropertyDef

ROOT = Path(__file__).parents[1]


def _contract_ontology() -> Ontology:
    ontology = load_ontology(ROOT / "examples" / "customer_support.yaml")
    actions = tuple(
        action.model_copy(
            update={
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
    return ontology.model_copy(update={"actions": actions})


def _migration_ontology(new: bool) -> Ontology:
    common_metadata = {
        "name": "Migration fixture",
        "version": "2.0.0" if new else "1.0.0",
        "id": "new-id" if new else "old-id",
        "namespace": "example.new" if new else "example.old",
    }
    if not new:
        entities = {
            "OldCustomer": {"properties": {"id": {"type": "string", "required": True}}},
            "Shared": {
                "properties": {
                    "legacy": {"type": "string"},
                    "count": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                        "default": 1,
                    },
                    "label": {"type": "string", "min_length": 1, "max_length": 20},
                    "removed": {"type": "string"},
                }
            },
            "Target": {"properties": {}},
        }
        relationships = [
            {
                "name": "renamed_link",
                "from": "Shared",
                "to": "Target",
                "cardinality": "one_to_one",
            },
            {
                "name": "stable_link",
                "from": "Shared",
                "to": "Target",
                "cardinality": "one_to_one",
            },
        ]
        actions = [
            {
                "name": "renamed_action",
                "subject": "Shared",
                "inputs": {"value": {"type": "string"}},
            },
            {
                "name": "stable_action",
                "subject": "Shared",
                "inputs": {
                    "changed": {"type": "integer"},
                    "removed": {"type": "string"},
                },
                "output": {"type": "string"},
                "permissions": ["example.use", "example.old"],
                "risk": "low",
                "review_required": False,
            },
        ]
        permissions = {"example.use": {}, "example.old": {}}
    else:
        entities = {
            "Customer": {
                "aliases": ["OldCustomer"],
                "properties": {"id": {"type": "string", "required": True}},
            },
            "Shared": {
                "properties": {
                    "current": {"type": "string", "aliases": ["legacy"]},
                    "count": {
                        "type": "integer",
                        "minimum": -1,
                        "maximum": 11,
                        "default": 2,
                    },
                    "label": {"type": "string", "min_length": 2, "max_length": 10},
                    "required_new": {"type": "string", "required": True},
                }
            },
            "Target": {"properties": {}},
            "Other": {"properties": {}},
        }
        relationships = [
            {
                "name": "new_link",
                "aliases": ["renamed_link"],
                "from": "Shared",
                "to": "Target",
                "cardinality": "one_to_one",
            },
            {
                "name": "stable_link",
                "from": "Customer",
                "to": "Other",
                "cardinality": "many_to_many",
            },
            {
                "name": "added_link",
                "from": "Shared",
                "to": "Other",
                "cardinality": "one_to_many",
            },
        ]
        actions = [
            {
                "name": "new_action",
                "aliases": ["renamed_action"],
                "subject": "Shared",
                "inputs": {"value": {"type": "string"}},
            },
            {
                "name": "stable_action",
                "subject": "Shared",
                "inputs": {
                    "changed": {"type": "string"},
                    "added": {"type": "string", "required": True},
                },
                "output": {"type": "integer"},
                "permissions": ["example.use"],
                "risk": "high",
                "review_required": True,
                "preconditions": ["external check"],
            },
        ]
        permissions = {"example.use": {}, "example.new": {}}
    return Ontology.model_validate(
        {
            "schema_version": "1.0",
            "ontology": common_metadata,
            "entities": entities,
            "relationships": relationships,
            "actions": actions,
            "permissions": permissions,
        }
    )


def test_action_schema_and_tool_contract_are_consistent() -> None:
    ontology = _contract_ontology()
    schema = action_input_schema(ontology, "issue_refund")
    output = action_output_schema(ontology, "issue_refund")
    tool = generate_tool_contract(ontology, "issue_refund")
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["required"] == ["amount", "reason"]
    assert schema["properties"]["amount"]["x-exact-decimal"] is True
    assert schema["properties"]["amount"]["anyOf"][1]["type"] == "string"
    assert output is not None
    assert {"$ref": "#/$defs/Refund"} in output["anyOf"]
    assert tool.input_schema == schema
    assert tool.output_schema == output
    assert tool.required_permissions == ("billing.refund",)
    assert tool.ontology.digest == ontology_digest(ontology)
    assert tool.to_dict()["schema_version"] == "1.0"


def test_all_neutral_contracts_share_ontology_identity() -> None:
    ontology = _contract_ontology()
    checked = check_action_contract(
        ontology,
        action="issue_refund",
        inputs={"amount": "5.00", "reason": "duplicate"},
        actor_permissions=["billing.refund"],
    )
    contracts = [
        generate_tool_contract(ontology, "issue_refund"),
        generate_policy_context(
            ontology,
            "issue_refund",
            actor="service",
            roles=["operator", "operator"],
            permissions=["billing.refund"],
            data_classifications=["financial"],
            tenant="fictional",
            project="support",
            operational_context={"tokens": 100},
        ),
        generate_audit_context(
            ontology,
            action="issue_refund",
            classification="financial",
            contract_result=checked,
            correlation={"request": "R-1"},
        ),
        generate_meter_attribution(
            ontology,
            action="issue_refund",
            workload="refund-review",
            team="support",
            outcome_category="reviewed",
            allocation_dimensions={"cost_center": "support"},
        ),
        generate_benchmark_fixture(
            ontology,
            "issue_refund",
            permitted_routes=["baseline_model"],
            quality_expectations=["correct classification"],
        ),
        generate_rag_metadata(
            ontology,
            entity_type="Invoice",
            entity_id="I-1",
            property_source="status",
            classification="financial",
            sensitivity="confidential",
            allowed_actions=["issue_refund"],
            permissions=["billing.refund"],
            retention="30 days",
            provenance={"source": "fictional"},
        ),
    ]
    identities = {json.dumps(item.ontology.to_dict(), sort_keys=True) for item in contracts}
    assert len(identities) == 1
    assert all(item.to_dict()["schema_version"] == "1.0" for item in contracts)


def test_contract_generation_rejects_unknown_meaning() -> None:
    ontology = _contract_ontology()
    with pytest.raises(KeyError):
        generate_tool_contract(ontology, "missing")
    with pytest.raises(KeyError):
        generate_rag_metadata(ontology, entity_type="Missing", entity_id="X")


def test_detailed_diff_and_migration_plan_are_deterministic() -> None:
    old = _migration_ontology(False)
    new = _migration_ontology(True)
    result = diff_ontologies(old, new)
    codes = {change.code for change in result.changes}
    assert {
        "ONTOLOGY_ID_CHANGED",
        "ONTOLOGY_NAMESPACE_CHANGED",
        "ENTITY_RENAMED",
        "PROPERTY_RENAMED",
        "PROPERTY_REMOVED",
        "PROPERTY_DEFAULT_CHANGED",
        "NUMERIC_LIMIT_RELAXED",
        "LENGTH_LIMIT_STRICTER",
        "RELATIONSHIP_RENAMED",
        "RELATIONSHIP_ADDED",
        "RELATIONSHIP_SOURCE_CHANGED",
        "RELATIONSHIP_TARGET_CHANGED",
        "CARDINALITY_CHANGED",
        "ACTION_RENAMED",
        "ACTION_INPUT_REMOVED",
        "ACTION_INPUT_TYPE_CHANGED",
        "REQUIRED_ACTION_INPUT_ADDED",
        "ACTION_OUTPUT_CHANGED",
        "ACTION_PERMISSION_RELAXED",
        "ACTION_RISK_CHANGED",
        "ACTION_REVIEW_CHANGED",
        "ACTION_PRECONDITIONS_CHANGED",
        "PERMISSION_REMOVED",
        "PERMISSION_ADDED",
    } <= codes

    first = build_migration_plan(old, new)
    second = build_migration_plan(old, new)
    assert first == second
    assert first.suggested_version_impact == "major"
    assert migration_plan_json(first) == migration_plan_json(second)
    markdown = migration_plan_markdown(first)
    assert markdown.startswith("# Ontology migration plan")
    assert "Automation:" in markdown
    assert json.loads(migration_plan_json(first))["schema_version"] == "1.0"


def test_empty_migration_plan_is_patch() -> None:
    ontology = _contract_ontology()
    plan = build_migration_plan(ontology, ontology)
    assert plan.steps == ()
    assert plan.suggested_version_impact == "patch"
    assert "No migration steps are required." in migration_plan_markdown(plan)


def test_diff_handles_structured_enums_and_migration_paths() -> None:
    old = _migration_ontology(False)
    new = _migration_ontology(True)
    old_shared = old.entities["Shared"]
    new_shared = new.entities["Shared"]
    old_entities = dict(old.entities)
    new_entities = dict(new.entities)
    old_entities["Shared"] = old_shared.model_copy(
        update={
            "properties": {
                **old_shared.properties,
                "choice": old_shared.properties["legacy"].model_copy(
                    update={"enum": ({"kind": ["shared"]}, "old")}
                ),
            }
        }
    )
    new_entities["Shared"] = new_shared.model_copy(
        update={
            "properties": {
                **new_shared.properties,
                "choice": new_shared.properties["current"].model_copy(
                    update={"enum": ({"kind": ["shared"]}, "new")}
                ),
            }
        }
    )
    renamed = new.entities["Customer"].model_copy(
        update={"aliases": ("HistoricalCustomer", "OldCustomer")}
    )
    new_entities["Customer"] = renamed
    old = old.model_copy(update={"entities": old_entities})
    new = new.model_copy(update={"entities": new_entities})

    result = diff_ontologies(old, new)
    assert {"ENUM_VALUE_ADDED", "ENUM_VALUE_REMOVED"} <= {change.code for change in result.changes}
    plan = build_migration_plan(old, new)
    entity_rename = next(step for step in plan.steps if step.code == "ENTITY_RENAMED")
    assert entity_rename.old_path == "entities.OldCustomer"
    enum_steps = [step for step in plan.steps if step.code.startswith("ENUM_VALUE_")]
    assert enum_steps
    assert all(step.old_path == step.new_path for step in enum_steps)


def test_required_action_input_with_explicit_default_is_not_reported_optional() -> None:
    old = _contract_ontology()
    action = old.actions[0]
    new_input = PropertyDef(type="string", required=True, nullable=True, default=None)
    changed_action = action.model_copy(update={"inputs": {**action.inputs, "new_input": new_input}})
    new = old.model_copy(update={"actions": (changed_action, *old.actions[1:])})
    codes = {change.code for change in diff_ontologies(old, new).changes}
    assert "REQUIRED_ACTION_INPUT_ADDED_WITH_DEFAULT" in codes
    assert "OPTIONAL_ACTION_INPUT_ADDED" not in codes
