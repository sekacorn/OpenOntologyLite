"""Versioned, vendor-neutral ecosystem contract models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Immutable contract base with stable serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Serialize without implementation-specific objects."""

        return self.model_dump(mode="json", exclude_none=True)


class OntologyIdentity(ContractModel):
    """Portable ontology provenance shared by every handoff contract."""

    ontology_id: str
    ontology_version: str
    namespace: str
    digest: str


class ToolContract(ContractModel):
    """Neutral tool description suitable for adapter consumption."""

    contract_type: str = "tool"
    name: str
    description: str = ""
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    required_permissions: tuple[str, ...] = ()
    risk: str
    review_required: bool
    audit_required: bool
    expected_audit_events: tuple[str, ...] = ()
    ontology: OntologyIdentity


class PolicyEvaluationContext(ContractModel):
    """Neutral policy request context; no policy decision is performed."""

    contract_type: str = "policy_evaluation_context"
    subject: str | None = None
    action: str
    actor: str | None = None
    roles: tuple[str, ...] = ()
    resource_entity: str | None = None
    resource_id: str | None = None
    permissions: tuple[str, ...] = ()
    data_classifications: tuple[str, ...] = ()
    risk: str
    requested_operation: str
    tenant: str | None = None
    project: str | None = None
    operational_context: dict[str, Any] = Field(default_factory=dict)
    ontology: OntologyIdentity


class AuditOntologyContext(ContractModel):
    """Neutral audit context; it does not append or sign an event."""

    contract_type: str = "audit_ontology_context"
    entity: str | None = None
    action: str | None = None
    classification: str | None = None
    risk: str
    contract_status: str | None = None
    review_required: bool
    escalation_expectations: tuple[str, ...] = ()
    correlation: dict[str, str] = Field(default_factory=dict)
    ontology: OntologyIdentity


class MeterAttributionContext(ContractModel):
    """Neutral outcome/cost allocation dimensions."""

    contract_type: str = "meter_attribution"
    entity: str | None = None
    action: str | None = None
    workload: str | None = None
    team: str | None = None
    project: str | None = None
    tenant: str | None = None
    customer: str | None = None
    outcome_category: str | None = None
    allocation_dimensions: dict[str, str] = Field(default_factory=dict)
    ontology: OntologyIdentity


class BenchmarkTaskFixture(ContractModel):
    """Neutral benchmark task description; it does not execute a workload."""

    contract_type: str = "benchmark_task"
    task_id: str
    description: str = ""
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    risk: str
    permitted_routes: tuple[str, ...] = ()
    review_required: bool
    escalation_expectations: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    audit_required: bool
    quality_expectations: tuple[str, ...] = ()
    ontology: OntologyIdentity


class RAGMetadata(ContractModel):
    """Portable metadata for a caller-managed RAG document."""

    contract_type: str = "rag_metadata"
    entity_type: str
    entity_id: str
    property_source: str | None = None
    classification: str
    sensitivity: str
    allowed_actions: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    tenant: str | None = None
    project: str | None = None
    retention: str | None = None
    provenance: dict[str, str] = Field(default_factory=dict)
    ontology: OntologyIdentity
