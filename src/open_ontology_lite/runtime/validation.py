"""Bounded runtime validation for ontology entity and action contracts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from open_ontology_lite.models import Ontology, PropertyDef, ValidationIssue
from open_ontology_lite.runtime.models import (
    ActionContractResult,
    ContractStatus,
    EntityValidationResult,
)

_UNSAFE_PATTERN = re.compile(r"[()|]|\\[1-9]")
_UNSET = object()


@dataclass(frozen=True)
class RuntimeLimits:
    """Resource limits applied to untrusted runtime values."""

    max_depth: int = 24
    max_collection_items: int = 10_000
    max_string_length: int = 100_000
    max_pattern_input: int = 4_096
    max_pattern_length: int = 256
    max_issues: int = 1_000


class _Collector:
    def __init__(self, limits: RuntimeLimits) -> None:
        self.limits = limits
        self.issues: list[ValidationIssue] = []
        self.truncated = False

    def add(
        self,
        severity: str,
        code: str,
        message: str,
        path: str,
        suggestion: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        if len(self.issues) >= self.limits.max_issues:
            self.truncated = True
            return
        self.issues.append(
            ValidationIssue(
                severity=severity,  # type: ignore[arg-type]
                code=code,
                message=message,
                path=path,
                suggestion=suggestion,
                context=context or {},
            )
        )

    def finish(self) -> tuple[ValidationIssue, ...]:
        if self.truncated and len(self.issues) < self.limits.max_issues + 1:
            self.issues.append(
                ValidationIssue(
                    severity="error",
                    code="DIAGNOSTIC_LIMIT_REACHED",
                    message="Validation stopped after reaching the diagnostic limit.",
                    path="<root>",
                    suggestion="Resolve reported issues before validating again.",
                    context={"limit": self.limits.max_issues},
                )
            )
        return tuple(self.issues)


@dataclass
class _ValidationState:
    ontology: Ontology
    collector: _Collector
    strict: bool
    aliases_required: bool = False
    defaults_required: bool = False


def _context(value: Any) -> dict[str, Any]:
    context: dict[str, Any] = {"received_type": type(value).__name__}
    if isinstance(value, (str, bytes, Mapping, Sequence)):
        context["length"] = len(value)
    return context


def _has_default(prop: PropertyDef) -> bool:
    return "default" in prop.model_fields_set


def _decimal(value: Any, *, allow_float: bool) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        candidate = value
    elif isinstance(value, int):
        candidate = Decimal(value)
    elif isinstance(value, str):
        try:
            candidate = Decimal(value.strip())
        except InvalidOperation:
            return None
    elif allow_float and isinstance(value, float) and math.isfinite(value):
        candidate = Decimal(str(value))
    else:
        return None
    return candidate if candidate.is_finite() else None


def _primitive(prop: PropertyDef, value: Any, path: str, state: _ValidationState) -> Any:
    if value is None:
        if prop.nullable:
            return None
        state.collector.add("error", "NULL_NOT_ALLOWED", "Null is not allowed.", path)
        return None
    if prop.type == "string":
        if not isinstance(value, str):
            return _type_error(prop, value, path, state)
        normalized: Any = value
    elif prop.type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return _type_error(prop, value, path, state)
        normalized = value
    elif prop.type in {"number", "decimal"}:
        number = _decimal(value, allow_float=prop.type == "number")
        if number is None:
            code = (
                "UNSAFE_DECIMAL_FLOAT"
                if prop.type == "decimal" and isinstance(value, float)
                else "TYPE_MISMATCH"
            )
            suggestion = (
                "Provide decimal values as strings, integers, or Decimal instances."
                if code == "UNSAFE_DECIMAL_FLOAT"
                else None
            )
            state.collector.add(
                "error",
                code,
                f"Expected {prop.type}.",
                path,
                suggestion,
                _context(value),
            )
            return None
        normalized = number
    elif prop.type == "boolean":
        if not isinstance(value, bool):
            return _type_error(prop, value, path, state)
        normalized = value
    elif prop.type == "date":
        if not isinstance(value, str):
            return _type_error(prop, value, path, state)
        try:
            normalized = date.fromisoformat(value).isoformat()
        except ValueError:
            state.collector.add("error", "INVALID_DATE", "Expected an ISO 8601 date.", path)
            return None
    elif prop.type == "datetime":
        if not isinstance(value, str):
            return _type_error(prop, value, path, state)
        try:
            normalized = datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            state.collector.add("error", "INVALID_DATETIME", "Expected an ISO 8601 datetime.", path)
            return None
    elif prop.type == "uuid":
        if not isinstance(value, str):
            return _type_error(prop, value, path, state)
        try:
            normalized = str(UUID(value))
        except ValueError:
            state.collector.add("error", "INVALID_UUID", "Expected a valid UUID.", path)
            return None
    else:
        return value
    _validate_constraints(prop, normalized, path, state)
    return normalized


def _type_error(prop: PropertyDef, value: Any, path: str, state: _ValidationState) -> None:
    state.collector.add(
        "error",
        "TYPE_MISMATCH",
        f"Expected {prop.type}.",
        path,
        context=_context(value),
    )
    return None


def _validate_constraints(
    prop: PropertyDef, value: Any, path: str, state: _ValidationState
) -> None:
    if isinstance(value, str):
        if len(value) > state.collector.limits.max_string_length:
            state.collector.add(
                "error",
                "STRING_LIMIT_EXCEEDED",
                "String exceeds the runtime size limit.",
                path,
                context={"length": len(value), "limit": state.collector.limits.max_string_length},
            )
            return
        if prop.pattern:
            if len(
                prop.pattern
            ) > state.collector.limits.max_pattern_length or _UNSAFE_PATTERN.search(prop.pattern):
                state.collector.add(
                    "error",
                    "UNSAFE_PATTERN",
                    "Pattern is outside the bounded runtime pattern subset.",
                    path,
                )
            elif len(value) > state.collector.limits.max_pattern_input:
                state.collector.add(
                    "error",
                    "PATTERN_INPUT_LIMIT_EXCEEDED",
                    "String is too large for bounded pattern validation.",
                    path,
                )
            else:
                try:
                    matches = re.fullmatch(prop.pattern, value) is not None
                except re.error:
                    state.collector.add("error", "INVALID_PATTERN", "Pattern is invalid.", path)
                else:
                    if not matches:
                        state.collector.add(
                            "error", "PATTERN_MISMATCH", "String does not match the pattern.", path
                        )
    length = len(value) if isinstance(value, (str, list, tuple, dict)) else None
    if length is not None:
        if prop.min_length is not None and length < prop.min_length:
            state.collector.add(
                "error", "MIN_LENGTH", f"Length must be at least {prop.min_length}.", path
            )
        if prop.max_length is not None and length > prop.max_length:
            state.collector.add(
                "error", "MAX_LENGTH", f"Length must be at most {prop.max_length}.", path
            )
    if isinstance(value, (int, Decimal)) and not isinstance(value, bool):
        if prop.minimum is not None and value < Decimal(str(prop.minimum)):
            state.collector.add("error", "MINIMUM", f"Value must be at least {prop.minimum}.", path)
        if prop.maximum is not None and value > Decimal(str(prop.maximum)):
            state.collector.add("error", "MAXIMUM", f"Value must be at most {prop.maximum}.", path)
    if prop.enum is not None and value not in prop.enum:
        state.collector.add(
            "error",
            "ENUM_MISMATCH",
            "Value is not one of the declared enum values.",
            path,
            context={"allowed_count": len(prop.enum)},
        )


def _validate_reference(
    prop: PropertyDef,
    value: Any,
    path: str,
    state: _ValidationState,
    depth: int,
) -> Any:
    if value is None and prop.nullable:
        return None
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        if isinstance(value, str) and not value:
            state.collector.add("error", "EMPTY_REFERENCE", "Reference identifier is empty.", path)
            return None
        return value
    if not isinstance(value, Mapping):
        return _type_error(prop, value, path, state)
    if not prop.target or prop.target not in state.ontology.entities:
        state.collector.add(
            "error",
            "UNKNOWN_REFERENCE_TARGET",
            "Reference target is not declared in the ontology.",
            path,
        )
        return None
    return _validate_mapping(
        state.ontology.entities[prop.target].properties, value, path, state, depth + 1
    )


def _validate_property(
    prop: PropertyDef,
    value: Any,
    path: str,
    state: _ValidationState,
    depth: int,
) -> Any:
    if depth > state.collector.limits.max_depth:
        state.collector.add(
            "error", "MAX_DEPTH_EXCEEDED", "Runtime value exceeds the nesting limit.", path
        )
        return None
    if prop.type == "reference":
        normalized = _validate_reference(prop, value, path, state, depth)
    elif prop.type == "object":
        if value is None and prop.nullable:
            return None
        if not isinstance(value, Mapping):
            return _type_error(prop, value, path, state)
        normalized = _validate_mapping(prop.properties, value, path, state, depth + 1)
    elif prop.type == "array":
        if value is None and prop.nullable:
            return None
        if not isinstance(value, (list, tuple)):
            return _type_error(prop, value, path, state)
        if len(value) > state.collector.limits.max_collection_items:
            state.collector.add(
                "error",
                "COLLECTION_LIMIT_EXCEEDED",
                "Collection exceeds the runtime item limit.",
                path,
                context={
                    "length": len(value),
                    "limit": state.collector.limits.max_collection_items,
                },
            )
            return None
        item_def = prop.items_schema or PropertyDef(type=prop.items or "string")
        normalized = [
            _validate_property(item_def, item, f"{path}[{index}]", state, depth + 1)
            for index, item in enumerate(value)
        ]
        _validate_constraints(prop, normalized, path, state)
    else:
        normalized = _primitive(prop, value, path, state)
    return normalized


def _validate_mapping(
    definitions: Mapping[str, PropertyDef],
    value: Mapping[Any, Any],
    path: str,
    state: _ValidationState,
    depth: int,
) -> dict[str, Any]:
    if len(value) > state.collector.limits.max_collection_items:
        state.collector.add(
            "error",
            "COLLECTION_LIMIT_EXCEEDED",
            "Object exceeds the runtime property limit.",
            path,
            context={"length": len(value), "limit": state.collector.limits.max_collection_items},
        )
        return {}
    aliases: dict[str, str] = {}
    for canonical, definition in definitions.items():
        for alias in definition.aliases:
            aliases[alias] = canonical
    normalized: dict[str, Any] = {}
    supplied: set[str] = set()
    for raw_name, raw_value in value.items():
        if not isinstance(raw_name, str):
            state.collector.add(
                "error", "NON_STRING_PROPERTY", "Property names must be strings.", path
            )
            continue
        canonical = aliases.get(raw_name, raw_name)
        if canonical not in definitions:
            severity = "error" if state.strict else "warning"
            state.collector.add(
                severity,
                "UNKNOWN_PROPERTY",
                "An unknown property was supplied.",
                f"{path}.<unknown>",
                "Remove the property or declare it in the ontology.",
                context={"name_length": len(raw_name)},
            )
            continue
        if canonical in supplied:
            state.collector.add(
                "error",
                "ALIAS_COLLISION",
                f"Property '{canonical}' was supplied more than once through aliases.",
                f"{path}.{canonical}",
                "Supply only the canonical property or one alias.",
            )
            continue
        supplied.add(canonical)
        if raw_name != canonical:
            state.aliases_required = True
        normalized[canonical] = _validate_property(
            definitions[canonical], raw_value, f"{path}.{canonical}", state, depth
        )
    for canonical, definition in definitions.items():
        if canonical in supplied:
            continue
        if _has_default(definition):
            before = len(state.collector.issues)
            default_value = _validate_property(
                definition, definition.default, f"{path}.{canonical}", state, depth
            )
            if len(state.collector.issues) > before:
                state.collector.add(
                    "error",
                    "INVALID_DEFAULT",
                    f"Declared default for '{canonical}' is invalid.",
                    f"{path}.{canonical}",
                )
            else:
                normalized[canonical] = default_value
                state.defaults_required = True
        elif definition.required:
            state.collector.add(
                "error",
                "REQUIRED_PROPERTY_MISSING",
                f"Required property '{canonical}' is missing.",
                f"{path}.{canonical}",
            )
    return dict(sorted(normalized.items()))


def validate_entity_instance(
    ontology: Ontology,
    *,
    entity_type: str,
    value: Mapping[str, Any],
    strict: bool = True,
    limits: RuntimeLimits | None = None,
) -> EntityValidationResult:
    """Validate an entity instance without mutating the caller's value."""

    active_limits = limits or RuntimeLimits()
    collector = _Collector(active_limits)
    state = _ValidationState(ontology=ontology, collector=collector, strict=strict)
    resolved_name = entity_type
    if entity_type not in ontology.entities:
        matches = [
            name for name, entity in ontology.entities.items() if entity_type in entity.aliases
        ]
        if len(matches) == 1:
            resolved_name = matches[0]
            state.aliases_required = True
        else:
            collector.add(
                "error",
                "UNKNOWN_ENTITY_TYPE",
                "The requested entity type is not declared.",
                "entity_type",
                "Use a declared entity name or alias.",
            )
            return EntityValidationResult(
                valid=False,
                entity_type=entity_type,
                issues=collector.finish(),
            )
    normalized = _validate_mapping(
        ontology.entities[resolved_name].properties,
        value,
        resolved_name,
        state,
        0,
    )
    issues = collector.finish()
    valid = not any(issue.severity == "error" for issue in issues)
    return EntityValidationResult(
        valid=valid,
        entity_type=resolved_name,
        issues=issues,
        normalized_value=normalized if valid else None,
        aliases_required=state.aliases_required,
        defaults_required=state.defaults_required,
    )


def check_action_contract(
    ontology: Ontology,
    *,
    action: str,
    inputs: Mapping[str, Any],
    actor_permissions: Sequence[str] = (),
    context: Mapping[str, Any] | None = None,
    output: Any = _UNSET,
    strict: bool = True,
    limits: RuntimeLimits | None = None,
) -> ActionContractResult:
    """Check semantic contract satisfaction without making an authorization decision."""

    del context  # Reserved for future structured preconditions; strings are never executed.
    active_limits = limits or RuntimeLimits()
    collector = _Collector(active_limits)
    action_map = {item.name: item for item in ontology.actions}
    resolved_name = action
    if action not in action_map:
        matches = [item.name for item in ontology.actions if action in item.aliases]
        if len(matches) == 1:
            resolved_name = matches[0]
        else:
            collector.add(
                "error", "UNKNOWN_ACTION", "The requested action is not declared.", "action"
            )
            return ActionContractResult(
                status="unsatisfied", action=action, issues=collector.finish()
            )
    contract = action_map[resolved_name]
    state = _ValidationState(ontology=ontology, collector=collector, strict=strict)
    validated_inputs = _validate_mapping(contract.inputs, inputs, "inputs", state, 0)
    missing = tuple(sorted(set(contract.permissions) - set(actor_permissions)))
    for permission in missing:
        collector.add(
            "error",
            "MISSING_PERMISSION",
            f"Required permission '{permission}' is not present.",
            "actor_permissions",
            "Have the calling policy or authorization layer evaluate this permission.",
        )
    unresolved = tuple(contract.preconditions)
    for index, _precondition in enumerate(unresolved):
        collector.add(
            "warning",
            "PRECONDITION_UNRESOLVED",
            "Declarative precondition requires external evaluation.",
            f"actions.{resolved_name}.preconditions[{index}]",
            "Evaluate the precondition in a trusted policy or application runtime.",
        )
    validated_output: Any = None
    if output is not _UNSET:
        if contract.output is None:
            collector.add(
                "warning",
                "OUTPUT_CONTRACT_UNDECLARED",
                "An output was supplied but the action has no output contract.",
                "output",
            )
        else:
            validated_output = _validate_property(contract.output, output, "output", state, 0)
    issues = collector.finish()
    has_errors = any(issue.severity == "error" for issue in issues)
    status: ContractStatus = (
        "unsatisfied" if has_errors else ("indeterminate" if unresolved else "satisfied")
    )
    evidence = (
        f"actions.{resolved_name}",
        f"entities.{contract.subject}",
        *(f"permissions.{permission}" for permission in contract.permissions),
    )
    return ActionContractResult(
        status=status,
        action=resolved_name,
        issues=issues,
        validated_inputs=validated_inputs if not has_errors else None,
        validated_output=validated_output,
        required_permissions=tuple(sorted(contract.permissions)),
        missing_permissions=missing,
        unresolved_preconditions=unresolved,
        risk=contract.risk,
        review_required=contract.review_required,
        escalation_expectations=contract.escalation,
        audit_required=contract.audit_required,
        expected_audit_events=contract.expected_audit_events,
        evidence_paths=tuple(sorted(evidence)),
    )
