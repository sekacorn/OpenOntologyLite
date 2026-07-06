"""Semantic validation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from open_ontology_lite.models import Ontology, PropertyDef, ValidationIssue, ValidationReport
from open_ontology_lite.validation.constraints import validate_property_constraints
from open_ontology_lite.validation.identifiers import (
    MAX_PRECONDITION_LENGTH,
    has_control_characters,
    is_identifier,
    is_namespace,
    is_permission_name,
)

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
MAX_ENTITIES = 1_000
MAX_PROPERTIES = 20_000
MAX_RELATIONSHIPS = 10_000
MAX_ACTIONS = 5_000
MAX_PERMISSIONS = 10_000


def _issue(
    code: str,
    message: str,
    path: str,
    severity: str = "error",
    suggestion: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
        path=path,
        suggestion=suggestion,
    )


def _duplicates(values: Iterable[str]) -> set[str]:
    return {item for item, count in Counter(values).items() if count > 1}


def _validate_identifier(value: str, path: str, label: str) -> list[ValidationIssue]:
    if not value.strip():
        return [_issue("IDENTIFIER_EMPTY", f"{label} identifier is empty.", path)]
    if not is_identifier(value):
        return [_issue("IDENTIFIER_INVALID", f"{label} identifier '{value}' is invalid.", path)]
    return []


def _validate_property_references(
    prop: PropertyDef, path: str, entity_names: set[str]
) -> list[ValidationIssue]:
    issues = validate_property_constraints(prop, path)
    if prop.type == "reference" and prop.target and prop.target not in entity_names:
        issues.append(
            _issue(
                "PROPERTY_REFERENCE_TARGET_NOT_FOUND",
                f"Reference target entity '{prop.target}' is not declared.",
                f"{path}.target",
                suggestion=f"Declare entity '{prop.target}' or correct the target.",
            )
        )
    return issues


def validate_ontology(ontology: Ontology, *, strict_permissions: bool = True) -> ValidationReport:
    """Validate structural and semantic ontology rules."""

    issues: list[ValidationIssue] = []
    if ontology.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        issues.append(
            _issue(
                "SCHEMA_VERSION_UNSUPPORTED",
                f"Unsupported schema version '{ontology.schema_version}'.",
                "schema_version",
            )
        )
    if not is_namespace(ontology.ontology.namespace):
        issues.append(
            _issue("NAMESPACE_INVALID", "Ontology namespace is invalid.", "ontology.namespace")
        )
    issues.extend(
        _validate_identifier(ontology.ontology.id.replace("-", "_"), "ontology.id", "Ontology")
    )
    if not ontology.entities:
        issues.append(
            _issue("ONTOLOGY_EMPTY", "Ontology must declare at least one entity.", "entities")
        )
    if len(ontology.entities) > MAX_ENTITIES:
        issues.append(
            _issue(
                "ENTITY_LIMIT_EXCEEDED", "Entity count exceeds documented safety limit.", "entities"
            )
        )
    prop_count = sum(len(entity.properties) for entity in ontology.entities.values())
    if prop_count > MAX_PROPERTIES:
        issues.append(
            _issue(
                "PROPERTY_LIMIT_EXCEEDED",
                "Property count exceeds documented safety limit.",
                "entities",
            )
        )
    if len(ontology.relationships) > MAX_RELATIONSHIPS:
        issues.append(
            _issue(
                "RELATIONSHIP_LIMIT_EXCEEDED",
                "Relationship count exceeds documented safety limit.",
                "relationships",
            )
        )
    if len(ontology.actions) > MAX_ACTIONS:
        issues.append(
            _issue(
                "ACTION_LIMIT_EXCEEDED", "Action count exceeds documented safety limit.", "actions"
            )
        )
    if len(ontology.permissions) > MAX_PERMISSIONS:
        issues.append(
            _issue(
                "PERMISSION_LIMIT_EXCEEDED",
                "Permission count exceeds documented safety limit.",
                "permissions",
            )
        )

    entity_names = set(ontology.entities)
    for entity_name, entity in ontology.entities.items():
        issues.extend(_validate_identifier(entity_name, f"entities.{entity_name}", "Entity"))
        for prop_name, prop in entity.properties.items():
            issues.extend(
                _validate_identifier(
                    prop_name, f"entities.{entity_name}.properties.{prop_name}", "Property"
                )
            )
            issues.extend(
                _validate_property_references(
                    prop,
                    f"entities.{entity_name}.properties.{prop_name}",
                    entity_names,
                )
            )

    rel_names = [rel.name for rel in ontology.relationships]
    for duplicate in sorted(_duplicates(rel_names)):
        issues.append(
            _issue(
                "RELATIONSHIP_DUPLICATE",
                f"Duplicate relationship name '{duplicate}'.",
                "relationships",
            )
        )
    for index, rel in enumerate(ontology.relationships):
        path = f"relationships[{index}]"
        issues.extend(_validate_identifier(rel.name, f"{path}.name", "Relationship"))
        if rel.from_ not in entity_names:
            issues.append(
                _issue(
                    "RELATIONSHIP_SOURCE_NOT_FOUND",
                    f"Relationship '{rel.name}' references unknown source entity '{rel.from_}'.",
                    f"{path}.from",
                )
            )
        if rel.to not in entity_names:
            issues.append(
                _issue(
                    "RELATIONSHIP_TARGET_NOT_FOUND",
                    f"Relationship '{rel.name}' references unknown target entity '{rel.to}'.",
                    f"{path}.to",
                )
            )

    action_names = [action.name for action in ontology.actions]
    for duplicate in sorted(_duplicates(action_names)):
        issues.append(
            _issue("ACTION_DUPLICATE", f"Duplicate action name '{duplicate}'.", "actions")
        )
    declared_permissions = set(ontology.permissions)
    for index, action in enumerate(ontology.actions):
        path = f"actions[{index}]"
        issues.extend(_validate_identifier(action.name, f"{path}.name", "Action"))
        if action.subject not in entity_names:
            issues.append(
                _issue(
                    "ACTION_SUBJECT_NOT_FOUND",
                    f"Action '{action.name}' references unknown subject '{action.subject}'.",
                    f"{path}.subject",
                )
            )
        for input_name, prop in action.inputs.items():
            issues.extend(
                _validate_identifier(input_name, f"{path}.inputs.{input_name}", "Action input")
            )
            issues.extend(
                _validate_property_references(prop, f"{path}.inputs.{input_name}", entity_names)
            )
        if action.output is not None:
            issues.extend(
                _validate_property_references(action.output, f"{path}.output", entity_names)
            )
        for perm_index, permission in enumerate(action.permissions):
            if not permission:
                issues.append(
                    _issue(
                        "PERMISSION_EMPTY",
                        "Action permission name cannot be empty.",
                        f"{path}.permissions[{perm_index}]",
                    )
                )
            elif permission not in declared_permissions:
                severity = "error" if strict_permissions else "warning"
                issues.append(
                    _issue(
                        "PERMISSION_UNDECLARED",
                        f"Action '{action.name}' references undeclared permission '{permission}'.",
                        f"{path}.permissions[{perm_index}]",
                        severity,
                    )
                )
        for pre_index, precondition in enumerate(action.preconditions):
            pre_path = f"{path}.preconditions[{pre_index}]"
            if not isinstance(precondition, str) or not precondition.strip():
                issues.append(
                    _issue(
                        "PRECONDITION_EMPTY", "Precondition must be a nonempty string.", pre_path
                    )
                )
            elif len(precondition) > MAX_PRECONDITION_LENGTH:
                issues.append(
                    _issue(
                        "PRECONDITION_TOO_LONG",
                        "Precondition exceeds documented safe length.",
                        pre_path,
                    )
                )
            elif has_control_characters(precondition):
                issues.append(
                    _issue(
                        "PRECONDITION_CONTROL_CHARACTER",
                        "Precondition contains unsafe control characters.",
                        pre_path,
                    )
                )

    for permission in ontology.permissions:
        if not is_permission_name(permission):
            issues.append(
                _issue(
                    "PERMISSION_NAME_INVALID",
                    f"Permission name '{permission}' is invalid.",
                    f"permissions.{permission}",
                )
            )
    return ValidationReport(issues=tuple(issues))
