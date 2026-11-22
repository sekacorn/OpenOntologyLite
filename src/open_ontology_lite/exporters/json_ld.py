"""Deterministic JSON-LD envelope for lossless OpenOntologyLite transfer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from open_ontology_lite.errors import OntologyParseError
from open_ontology_lite.loading import load_value
from open_ontology_lite.loading.loader import validation_error_message
from open_ontology_lite.models import Ontology
from open_ontology_lite.normalization import normalize_ontology

JSON_LD_FORMAT_VERSION = "openontologylite.jsonld.v1"
JSON_LD_CONTEXT = {
    "@vocab": "https://github.com/sekacorn/OpenOntologyLite/ns/v1#",
    "format_version": "formatVersion",
    "ontology": "ontologyDocument",
}


def json_ld_document(ontology: Ontology) -> dict[str, Any]:
    """Return a JSON-LD document carrying the lossless normalized ontology."""

    return {
        "@context": JSON_LD_CONTEXT,
        "@type": "OntologyDocument",
        "format_version": JSON_LD_FORMAT_VERSION,
        "ontology": normalize_ontology(ontology),
    }


def json_ld_text(ontology: Ontology) -> str:
    """Return stable JSON-LD with a trailing newline."""

    return (
        json.dumps(
            json_ld_document(ontology),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


def ontology_from_json_ld(value: object) -> Ontology:
    """Validate a JSON-LD envelope and return its ontology."""

    if not isinstance(value, dict):
        raise OntologyParseError("JSON-LD root must be an object.")
    expected = {"@context", "@type", "format_version", "ontology"}
    if set(value) != expected:
        raise OntologyParseError("JSON-LD envelope fields are invalid.")
    if (
        value["@context"] != JSON_LD_CONTEXT
        or value["@type"] != "OntologyDocument"
        or value["format_version"] != JSON_LD_FORMAT_VERSION
    ):
        raise OntologyParseError("Unsupported OpenOntologyLite JSON-LD envelope.")
    try:
        return Ontology.model_validate(value["ontology"])
    except ValidationError as exc:
        raise OntologyParseError(
            f"Invalid JSON-LD ontology: {validation_error_message(exc)}"
        ) from exc


def load_json_ld(path: str | Path) -> Ontology:
    """Load a bounded local OpenOntologyLite JSON-LD file."""

    return ontology_from_json_ld(load_value(path))
