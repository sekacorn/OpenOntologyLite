"""Typed ontology migration plans."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from open_ontology_lite.models.diff import ChangeClass

AutomationSafety = Literal["safe", "unsafe", "unavailable"]
SemanticImpact = Literal["patch", "minor", "major"]


class MigrationStep(BaseModel):
    """One deterministic migration recommendation."""

    model_config = ConfigDict(frozen=True)

    code: str
    classification: ChangeClass
    old_path: str | None
    new_path: str | None
    explanation: str
    alias_available: bool = False
    migration: str
    automation: AutomationSafety
    semantic_version_impact: SemanticImpact
    evidence: tuple[str, ...] = ()


class MigrationPlan(BaseModel):
    """Machine-readable guidance for moving between ontology versions."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    ontology_id: str
    from_version: str
    to_version: str
    from_digest: str
    to_digest: str
    suggested_version_impact: SemanticImpact
    steps: tuple[MigrationStep, ...]

    def to_dict(self) -> dict[str, object]:
        """Return stable JSON-compatible plan data."""

        return self.model_dump(mode="json")
