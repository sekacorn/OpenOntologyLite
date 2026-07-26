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
from open_ontology_lite.diffing import diff_ontologies
from open_ontology_lite.inspection import inspect_ontology
from open_ontology_lite.loading import load_ontology
from open_ontology_lite.models import Ontology, ValidationReport
from open_ontology_lite.normalization import normalize_ontology, ontology_digest
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
    "EscalationPath",
    "ModelRoute",
    "Ontology",
    "ValidationReport",
    "ai_system_map_digest",
    "ai_system_map_mermaid",
    "ai_system_map_report",
    "diff_ontologies",
    "inspect_ontology",
    "load",
    "load_ai_system_map",
    "load_ontology",
    "normalize_ontology",
    "ontology_digest",
    "validate_ai_system_map",
    "validate_ontology",
]
