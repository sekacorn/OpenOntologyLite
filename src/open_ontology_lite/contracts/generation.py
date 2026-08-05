"""Deterministic generation of neutral ecosystem handoff contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from open_ontology_lite.contracts.models import (
    AuditOntologyContext,
    BenchmarkTaskFixture,
    MeterAttributionContext,
    OntologyIdentity,
    PolicyEvaluationContext,
    RAGMetadata,
    ToolContract,
)
from open_ontology_lite.exporters import action_input_schema, action_output_schema
from open_ontology_lite.models import ActionDef, Ontology
from open_ontology_lite.normalization import ontology_digest
from open_ontology_lite.runtime import ActionContractResult


def ontology_identity(ontology: Ontology) -> OntologyIdentity:
    """Build the common provenance object used by every contract."""

    return OntologyIdentity(
        ontology_id=ontology.ontology.id,
        ontology_version=ontology.ontology.version,
        namespace=ontology.ontology.namespace,
        digest=ontology_digest(ontology),
    )


def _action(ontology: Ontology, name: str) -> ActionDef:
    exact = [item for item in ontology.actions if item.name == name]
    if exact:
        return exact[0]
    aliases = [item for item in ontology.actions if name in item.aliases]
    if len(aliases) == 1:
        return aliases[0]
    raise KeyError(f"Unknown or ambiguous action: {name}")


def generate_tool_contract(ontology: Ontology, action: str) -> ToolContract:
    """Generate a Forge-compatible neutral tool description."""

    contract = _action(ontology, action)
    return ToolContract(
        name=contract.name,
        description=contract.description,
        input_schema=action_input_schema(ontology, contract),
        output_schema=action_output_schema(ontology, contract),
        required_permissions=tuple(sorted(contract.permissions)),
        risk=contract.risk,
        review_required=contract.review_required,
        audit_required=contract.audit_required,
        expected_audit_events=tuple(sorted(contract.expected_audit_events)),
        ontology=ontology_identity(ontology),
    )


def generate_policy_context(
    ontology: Ontology,
    action: str,
    *,
    actor: str | None = None,
    roles: Sequence[str] = (),
    resource_entity: str | None = None,
    resource_id: str | None = None,
    permissions: Sequence[str] = (),
    data_classifications: Sequence[str] = (),
    tenant: str | None = None,
    project: str | None = None,
    operational_context: Mapping[str, Any] | None = None,
) -> PolicyEvaluationContext:
    """Generate a neutral request context for an external policy engine."""

    contract = _action(ontology, action)
    return PolicyEvaluationContext(
        subject=contract.subject,
        action=contract.name,
        actor=actor,
        roles=tuple(sorted(set(roles))),
        resource_entity=resource_entity or contract.subject,
        resource_id=resource_id,
        permissions=tuple(sorted(set(permissions))),
        data_classifications=tuple(sorted(set(data_classifications))),
        risk=contract.risk,
        requested_operation=contract.name,
        tenant=tenant,
        project=project,
        operational_context=dict(sorted((operational_context or {}).items())),
        ontology=ontology_identity(ontology),
    )


def generate_audit_context(
    ontology: Ontology,
    *,
    entity: str | None = None,
    action: str | None = None,
    classification: str | None = None,
    contract_result: ActionContractResult | None = None,
    correlation: Mapping[str, str] | None = None,
) -> AuditOntologyContext:
    """Generate ontology context for a caller-managed audit event."""

    contract = _action(ontology, action) if action else None
    return AuditOntologyContext(
        entity=entity or (contract.subject if contract else None),
        action=contract.name if contract else None,
        classification=classification,
        risk=contract_result.risk
        if contract_result
        else (contract.risk if contract else "unknown"),
        contract_status=contract_result.status if contract_result else None,
        review_required=(
            contract_result.review_required
            if contract_result
            else bool(contract and contract.review_required)
        ),
        escalation_expectations=(
            contract_result.escalation_expectations
            if contract_result
            else (contract.escalation if contract else ())
        ),
        correlation=dict(sorted((correlation or {}).items())),
        ontology=ontology_identity(ontology),
    )


def generate_meter_attribution(
    ontology: Ontology,
    *,
    entity: str | None = None,
    action: str | None = None,
    workload: str | None = None,
    team: str | None = None,
    project: str | None = None,
    tenant: str | None = None,
    customer: str | None = None,
    outcome_category: str | None = None,
    allocation_dimensions: Mapping[str, str] | None = None,
) -> MeterAttributionContext:
    """Generate neutral attribution metadata without calculating costs."""

    contract = _action(ontology, action) if action else None
    return MeterAttributionContext(
        entity=entity or (contract.subject if contract else None),
        action=contract.name if contract else None,
        workload=workload,
        team=team,
        project=project,
        tenant=tenant,
        customer=customer,
        outcome_category=outcome_category,
        allocation_dimensions=dict(sorted((allocation_dimensions or {}).items())),
        ontology=ontology_identity(ontology),
    )


def generate_benchmark_fixture(
    ontology: Ontology,
    action: str,
    *,
    permitted_routes: Sequence[str] = (),
    quality_expectations: Sequence[str] = (),
) -> BenchmarkTaskFixture:
    """Generate a neutral task fixture for an external benchmark runner."""

    contract = _action(ontology, action)
    return BenchmarkTaskFixture(
        task_id=contract.name,
        description=contract.description,
        input_schema=action_input_schema(ontology, contract),
        output_schema=action_output_schema(ontology, contract),
        risk=contract.risk,
        permitted_routes=tuple(sorted(set(permitted_routes))),
        review_required=contract.review_required,
        escalation_expectations=tuple(sorted(contract.escalation)),
        required_permissions=tuple(sorted(contract.permissions)),
        audit_required=contract.audit_required,
        quality_expectations=tuple(sorted(set(quality_expectations))),
        ontology=ontology_identity(ontology),
    )


def generate_rag_metadata(
    ontology: Ontology,
    *,
    entity_type: str,
    entity_id: str,
    property_source: str | None = None,
    classification: str = "internal",
    sensitivity: str = "unknown",
    allowed_actions: Sequence[str] = (),
    permissions: Sequence[str] = (),
    tenant: str | None = None,
    project: str | None = None,
    retention: str | None = None,
    provenance: Mapping[str, str] | None = None,
) -> RAGMetadata:
    """Generate portable metadata for caller-managed RAG ingestion."""

    if entity_type not in ontology.entities:
        raise KeyError(f"Unknown entity type: {entity_type}")
    return RAGMetadata(
        entity_type=entity_type,
        entity_id=entity_id,
        property_source=property_source,
        classification=classification,
        sensitivity=sensitivity,
        allowed_actions=tuple(sorted(set(allowed_actions))),
        permissions=tuple(sorted(set(permissions))),
        tenant=tenant,
        project=project,
        retention=retention,
        provenance=dict(sorted((provenance or {}).items())),
        ontology=ontology_identity(ontology),
    )
