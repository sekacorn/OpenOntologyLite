"""Deterministic migration-plan generation."""

from __future__ import annotations

import json
from collections.abc import Mapping

from open_ontology_lite.diffing import diff_ontologies
from open_ontology_lite.models import Ontology
from open_ontology_lite.models.diff import DiffChange
from open_ontology_lite.normalization import ontology_digest

from .models import AutomationSafety, MigrationPlan, MigrationStep, SemanticImpact

_RENAME_CODES = {
    "ENTITY_RENAMED",
    "PROPERTY_RENAMED",
    "RELATIONSHIP_RENAMED",
    "ACTION_RENAMED",
}
_AUTOMATABLE_CODES = _RENAME_CODES | {
    "OPTIONAL_PROPERTY_ADDED",
    "REQUIRED_PROPERTY_ADDED_WITH_DEFAULT",
    "REQUIRED_ACTION_INPUT_ADDED_WITH_DEFAULT",
}
_UNSAFE_CODES = {
    "ENTITY_REMOVED",
    "PROPERTY_REMOVED",
    "PROPERTY_TYPE_CHANGED",
    "RELATIONSHIP_REMOVED",
    "RELATIONSHIP_SOURCE_CHANGED",
    "RELATIONSHIP_TARGET_CHANGED",
    "CARDINALITY_CHANGED",
    "ACTION_REMOVED",
    "ACTION_INPUT_REMOVED",
    "ACTION_INPUT_TYPE_CHANGED",
    "ACTION_OUTPUT_CHANGED",
    "PERMISSION_REMOVED",
    "ONTOLOGY_ID_CHANGED",
}
_DECLARATION_REMOVALS = {
    "ENTITY_REMOVED",
    "PROPERTY_REMOVED",
    "RELATIONSHIP_REMOVED",
    "ACTION_REMOVED",
    "ACTION_INPUT_REMOVED",
    "PERMISSION_REMOVED",
}
_DECLARATION_ADDITIONS = {
    "ENTITY_ADDED",
    "OPTIONAL_PROPERTY_ADDED",
    "REQUIRED_PROPERTY_ADDED",
    "REQUIRED_PROPERTY_ADDED_WITH_DEFAULT",
    "RELATIONSHIP_ADDED",
    "ACTION_ADDED",
    "OPTIONAL_ACTION_INPUT_ADDED",
    "REQUIRED_ACTION_INPUT_ADDED",
    "REQUIRED_ACTION_INPUT_ADDED_WITH_DEFAULT",
    "PERMISSION_ADDED",
}


def _impact(classification: str) -> SemanticImpact:
    if classification == "breaking":
        return "major"
    if classification in {"potentially_breaking", "non_breaking"}:
        return "minor"
    return "patch"


def _automation(change: DiffChange) -> AutomationSafety:
    if change.code in _AUTOMATABLE_CODES:
        return "safe"
    if change.code in _UNSAFE_CODES:
        return "unsafe"
    return "unavailable"


def _rename_paths(
    change: DiffChange, old: Ontology, new: Ontology
) -> tuple[str | None, str | None]:
    new_path = change.path
    if change.code == "ENTITY_RENAMED":
        new_name = new_path.split(".")[1]
        removed_names = set(old.entities) - set(new.entities)
        old_name = next(
            (name for name in sorted(removed_names) if name in new.entities[new_name].aliases),
            None,
        )
        return f"entities.{old_name}" if old_name else None, f"entities.{new_name}"
    if change.code == "PROPERTY_RENAMED":
        parts = new_path.split(".")
        new_name = parts[3]
        aliases = new.entities[parts[1]].properties[new_name].aliases
        old_properties = set(old.entities[parts[1]].properties)
        new_properties = set(new.entities[parts[1]].properties)
        old_name = next(
            (name for name in sorted(old_properties - new_properties) if name in aliases),
            None,
        )
        old_path = f"entities.{parts[1]}.properties.{old_name}" if old_name else None
        return old_path, ".".join(parts[:4])
    if change.code == "RELATIONSHIP_RENAMED":
        new_name = new_path.split(".")[1]
        relation = next(item for item in new.relationships if item.name == new_name)
        old_names = {item.name for item in old.relationships}
        new_names = {item.name for item in new.relationships}
        old_name = next(
            (name for name in sorted(old_names - new_names) if name in relation.aliases), None
        )
        return f"relationships.{old_name}" if old_name else None, f"relationships.{new_name}"
    if change.code == "ACTION_RENAMED":
        new_name = new_path.split(".")[1]
        action = next(item for item in new.actions if item.name == new_name)
        old_names = {item.name for item in old.actions}
        new_names = {item.name for item in new.actions}
        old_name = next(
            (name for name in sorted(old_names - new_names) if name in action.aliases), None
        )
        return f"actions.{old_name}" if old_name else None, f"actions.{new_name}"
    # Value-level enum changes keep the same declaration path; only exact
    # declaration changes may omit one side of a migration step.
    if change.code in _DECLARATION_REMOVALS:
        return change.path, None
    if change.code in _DECLARATION_ADDITIONS:
        return None, change.path
    return change.path, change.path


def _migration_text(change: DiffChange, automation: AutomationSafety) -> str:
    if change.code in _RENAME_CODES:
        return "Migrate consumers to the new name while retaining the declared alias."
    if change.code in {"REQUIRED_PROPERTY_ADDED", "PROPERTY_BECAME_REQUIRED"}:
        return "Backfill a valid value before adopting the new contract."
    if change.code == "REQUIRED_PROPERTY_ADDED_WITH_DEFAULT":
        return (
            "Apply or accept the declared default, then persist canonical values when appropriate."
        )
    if change.code in {"PROPERTY_REMOVED", "ACTION_INPUT_REMOVED"}:
        return "Stop producing the removed field and preserve data separately if required."
    if change.code in {"PROPERTY_TYPE_CHANGED", "ACTION_INPUT_TYPE_CHANGED"}:
        return "Define and test an explicit value conversion; do not coerce ambiguous data."
    if change.code.startswith("ACTION_PERMISSION") or change.code == "PERMISSION_REMOVED":
        return "Update policy configuration and permission references before rollout."
    if automation == "unsafe":
        return "Review affected data and integrations; automated migration is not safe."
    return change.suggestion or "Review the contract change and update affected consumers."


def build_migration_plan(old: Ontology, new: Ontology) -> MigrationPlan:
    """Build deterministic, non-mutating migration guidance."""

    steps: list[MigrationStep] = []
    for change in diff_ontologies(old, new).changes:
        old_path, new_path = _rename_paths(change, old, new)
        automation = _automation(change)
        steps.append(
            MigrationStep(
                code=change.code,
                classification=change.classification,
                old_path=old_path,
                new_path=new_path,
                explanation=change.message,
                alias_available=change.code in _RENAME_CODES,
                migration=_migration_text(change, automation),
                automation=automation,
                semantic_version_impact=_impact(change.classification),
                evidence=(change.path,),
            )
        )
    impact_order: Mapping[SemanticImpact, int] = {"patch": 0, "minor": 1, "major": 2}
    overall: SemanticImpact = max(
        (step.semantic_version_impact for step in steps),
        key=impact_order.__getitem__,
        default="patch",
    )
    return MigrationPlan(
        ontology_id=new.ontology.id,
        from_version=old.ontology.version,
        to_version=new.ontology.version,
        from_digest=ontology_digest(old),
        to_digest=ontology_digest(new),
        suggested_version_impact=overall,
        steps=tuple(steps),
    )


def migration_plan_json(plan: MigrationPlan) -> str:
    """Render a stable JSON migration plan."""

    return json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n"


def migration_plan_markdown(plan: MigrationPlan) -> str:
    """Render a compact readable migration plan."""

    lines = [
        "# Ontology migration plan",
        "",
        f"- Ontology: {plan.ontology_id}",
        f"- Versions: {plan.from_version} to {plan.to_version}",
        f"- Suggested semantic-version impact: {plan.suggested_version_impact}",
        f"- Source digest: {plan.from_digest}",
        f"- Target digest: {plan.to_digest}",
        "",
    ]
    if not plan.steps:
        lines.append("No migration steps are required.")
    for index, step in enumerate(plan.steps, start=1):
        lines.extend(
            [
                f"## {index}. {step.code}",
                "",
                f"- Classification: {step.classification}",
                f"- Old path: {step.old_path or 'not applicable'}",
                f"- New path: {step.new_path or 'not applicable'}",
                f"- Alias available: {'yes' if step.alias_available else 'no'}",
                f"- Automation: {step.automation}",
                f"- Semantic-version impact: {step.semantic_version_impact}",
                "",
                step.explanation,
                "",
                f"Migration: {step.migration}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
