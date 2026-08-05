"""Models for resolved local ontology modules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from open_ontology_lite.models import Ontology


class ModuleProvenance(BaseModel):
    """Origin and integrity information for one loaded module."""

    model_config = ConfigDict(frozen=True)

    namespace: str
    version: str
    digest: str
    path: str


class ResolvedOntology(BaseModel):
    """A merged ontology and deterministic definition provenance."""

    model_config = ConfigDict(frozen=True)

    ontology: Ontology
    modules: tuple[ModuleProvenance, ...]
    provenance: dict[str, str]
