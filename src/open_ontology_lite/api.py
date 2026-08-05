"""Public Python API for OpenOntologyLite."""

from pathlib import Path

from open_ontology_lite.ai_map import (
    AIEntity,
    AIIntegration,
    AISystemMap,
    AISystemMapValidationResult,
    AISystemMetadata,
    AITask,
    EscalationPath,
    ModelRoute,
    ai_system_map_digest,
    ai_system_map_mermaid,
    ai_system_map_report,
    load_ai_system_map,
    validate_ai_system_map,
)
from open_ontology_lite.contracts import (
    AuditOntologyContext,
    BenchmarkTaskFixture,
    MeterAttributionContext,
    PolicyEvaluationContext,
    RAGMetadata,
    ToolContract,
    generate_audit_context,
    generate_benchmark_fixture,
    generate_meter_attribution,
    generate_policy_context,
    generate_rag_metadata,
    generate_tool_contract,
)
from open_ontology_lite.diffing import diff_ontologies
from open_ontology_lite.exporters import action_input_schema, action_output_schema
from open_ontology_lite.inspection import inspect_ontology
from open_ontology_lite.loading import load_ontology
from open_ontology_lite.migrations import MigrationPlan, build_migration_plan
from open_ontology_lite.models import Ontology, ValidationReport
from open_ontology_lite.modules import ResolvedOntology, resolve_local_modules
from open_ontology_lite.normalization import normalize_ontology, ontology_digest
from open_ontology_lite.runtime import (
    ActionContractResult,
    EntityValidationResult,
    RuntimeLimits,
    check_action_contract,
    validate_entity_instance,
)
from open_ontology_lite.validation import validate_ontology


def load(path: str | Path) -> Ontology:
    """Load an ontology from YAML or JSON."""

    return load_ontology(path)


__all__ = [
    "AIEntity",
    "AIIntegration",
    "AISystemMap",
    "AISystemMapValidationResult",
    "AISystemMetadata",
    "AITask",
    "ActionContractResult",
    "AuditOntologyContext",
    "BenchmarkTaskFixture",
    "EntityValidationResult",
    "EscalationPath",
    "MeterAttributionContext",
    "MigrationPlan",
    "ModelRoute",
    "Ontology",
    "PolicyEvaluationContext",
    "RAGMetadata",
    "ResolvedOntology",
    "RuntimeLimits",
    "ToolContract",
    "ValidationReport",
    "action_input_schema",
    "action_output_schema",
    "ai_system_map_digest",
    "ai_system_map_mermaid",
    "ai_system_map_report",
    "build_migration_plan",
    "check_action_contract",
    "diff_ontologies",
    "generate_audit_context",
    "generate_benchmark_fixture",
    "generate_meter_attribution",
    "generate_policy_context",
    "generate_rag_metadata",
    "generate_tool_contract",
    "inspect_ontology",
    "load",
    "load_ai_system_map",
    "load_ontology",
    "normalize_ontology",
    "ontology_digest",
    "resolve_local_modules",
    "validate_ai_system_map",
    "validate_entity_instance",
    "validate_ontology",
]
