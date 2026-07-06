"""Public Python API for OpenOntologyLite."""

from pathlib import Path

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
    "Ontology",
    "ValidationReport",
    "diff_ontologies",
    "inspect_ontology",
    "load",
    "load_ontology",
    "normalize_ontology",
    "ontology_digest",
    "validate_ontology",
]
