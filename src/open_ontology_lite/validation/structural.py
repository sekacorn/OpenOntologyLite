"""Structural validation entry point."""

from open_ontology_lite.models import Ontology, ValidationReport
from open_ontology_lite.validation.semantic import validate_ontology


def validate_structure(ontology: Ontology) -> ValidationReport:
    """Run structural validation.

    Pydantic performs root shape, type, and unknown-field validation during loading;
    this function returns any model-level issues that remain visible after parsing.
    """

    return validate_ontology(ontology)
