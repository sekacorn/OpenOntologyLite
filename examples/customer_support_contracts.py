"""Complete offline semantic-contract walkthrough using fictional data."""

from __future__ import annotations

import json
from pathlib import Path

from open_ontology_lite import (
    ai_system_map_mermaid,
    ai_system_map_report,
    build_migration_plan,
    check_action_contract,
    generate_audit_context,
    generate_benchmark_fixture,
    generate_meter_attribution,
    generate_policy_context,
    generate_rag_metadata,
    generate_tool_contract,
    load_ai_system_map,
    load_ontology,
    validate_ai_system_map,
    validate_entity_instance,
)
from open_ontology_lite.migrations import migration_plan_json
from open_ontology_lite.models import PropertyDef

BASE = Path(__file__).resolve().parent


def main() -> None:
    """Run every executable-contract boundary without network access."""

    ontology = load_ontology(BASE / "customer_support.yaml")
    entity_result = validate_entity_instance(
        ontology,
        entity_type="Customer",
        value={"customer_id": "C-1042"},
    )
    action_result = check_action_contract(
        ontology,
        action="create_ticket",
        inputs={
            "customer_id": "C-1042",
            "description": "Unable to sign in to the fictional account.",
        },
        actor_permissions=["support.ticket.create"],
    )

    tool = generate_tool_contract(ontology, "create_ticket")
    policy = generate_policy_context(
        ontology,
        "create_ticket",
        actor="fictional-support-service",
        roles=["support_operator"],
        resource_entity="Customer",
        resource_id="C-1042",
        permissions=["support.ticket.create"],
        tenant="fictional-tenant",
        project="customer-support",
    )
    audit = generate_audit_context(
        ontology,
        entity="SupportTicket",
        action="create_ticket",
        classification="confidential",
        contract_result=action_result,
        correlation={"request_id": "REQ-100"},
    )
    meter = generate_meter_attribution(
        ontology,
        entity="SupportTicket",
        action="create_ticket",
        workload="ticket-intake",
        team="support",
        project="customer-support",
        outcome_category="contract_checked",
        allocation_dimensions={"cost_center": "support"},
    )
    benchmark = generate_benchmark_fixture(
        ontology,
        "create_ticket",
        permitted_routes=["baseline_model"],
        quality_expectations=["valid structured ticket input"],
    )
    rag = generate_rag_metadata(
        ontology,
        entity_type="Customer",
        entity_id="C-1042",
        property_source="account_status",
        classification="support",
        sensitivity="confidential",
        allowed_actions=["create_ticket"],
        permissions=["support.ticket.create"],
        tenant="fictional-tenant",
        retention="follow the fictional support retention policy",
        provenance={"source": "fictional example"},
    )

    customer = ontology.entities["Customer"]
    properties = {
        **customer.properties,
        "preferred_language": PropertyDef(type="string", default="en"),
    }
    next_ontology = ontology.model_copy(
        update={
            "ontology": ontology.ontology.model_copy(update={"version": "1.1.0"}),
            "entities": {
                **ontology.entities,
                "Customer": customer.model_copy(update={"properties": properties}),
            },
        }
    )
    migration = build_migration_plan(ontology, next_ontology)

    ai_map = load_ai_system_map(BASE / "ai_system_map" / "customer_support_ai.yaml")
    ai_validation = validate_ai_system_map(ai_map, ontology)
    report = ai_system_map_report(ai_map, validation=ai_validation)
    diagram = ai_system_map_mermaid(ai_map)

    identities = {
        contract.ontology.digest for contract in (tool, policy, audit, meter, benchmark, rag)
    }
    summary = {
        "entity_valid": entity_result.valid,
        "entity_defaults_required": entity_result.defaults_required,
        "action_status": action_result.status,
        "contract_types": [
            tool.contract_type,
            policy.contract_type,
            audit.contract_type,
            meter.contract_type,
            benchmark.contract_type,
            rag.contract_type,
        ],
        "shared_ontology_identity": len(identities) == 1,
        "migration": json.loads(migration_plan_json(migration)),
        "ai_map_valid": ai_validation.valid,
        "ai_map_report_generated": report.startswith("# AI System Map Report"),
        "ai_map_mermaid_generated": diagram.startswith("flowchart TD"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
