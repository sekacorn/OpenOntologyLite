"""Inspection summaries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from open_ontology_lite.models import Ontology
from open_ontology_lite.normalization import ontology_digest
from open_ontology_lite.validation import find_cycles, validate_ontology


class InspectionSummary(BaseModel):
    """Concise ontology summary."""

    model_config = ConfigDict(frozen=True)

    ontology_id: str
    version: str
    namespace: str
    entity_count: int
    property_count: int
    relationship_count: int
    action_count: int
    permission_count: int
    cycle_count: int
    validation_error_count: int
    warning_count: int
    canonical_digest: str


def inspect_ontology(ontology: Ontology) -> InspectionSummary:
    """Inspect an ontology and return stable summary data."""

    report = validate_ontology(ontology)
    return InspectionSummary(
        ontology_id=ontology.ontology.id,
        version=ontology.ontology.version,
        namespace=ontology.ontology.namespace,
        entity_count=len(ontology.entities),
        property_count=sum(len(entity.properties) for entity in ontology.entities.values()),
        relationship_count=len(ontology.relationships),
        action_count=len(ontology.actions),
        permission_count=len(ontology.permissions),
        cycle_count=len(find_cycles(ontology)),
        validation_error_count=len(report.errors),
        warning_count=len(report.warnings),
        canonical_digest=ontology_digest(ontology),
    )
