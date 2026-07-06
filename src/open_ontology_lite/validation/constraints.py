"""Property constraint validation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from open_ontology_lite.models import PropertyDef, ValidationIssue

NUMERIC_TYPES = {"integer", "number", "decimal"}
STRING_TYPES = {"string", "date", "datetime", "uuid"}


def _issue(code: str, message: str, path: str, suggestion: str | None = None) -> ValidationIssue:
    return ValidationIssue(
        severity="error", code=code, message=message, path=path, suggestion=suggestion
    )


def value_matches_type(value: Any, property_type: str) -> bool:
    """Return whether a Python value is compatible with an ontology property type."""

    if value is None:
        return True
    if property_type in {"string", "date", "datetime", "uuid", "reference"}:
        return isinstance(value, str)
    if property_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if property_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if property_type == "decimal":
        try:
            Decimal(str(value))
        except (InvalidOperation, ValueError):
            return False
        return not isinstance(value, bool)
    if property_type == "boolean":
        return isinstance(value, bool)
    if property_type == "object":
        return isinstance(value, dict)
    if property_type == "array":
        return isinstance(value, list)
    return False


def validate_property_constraints(prop: PropertyDef, path: str) -> list[ValidationIssue]:
    """Validate constraint compatibility for a property."""

    issues: list[ValidationIssue] = []
    if prop.pattern is not None and prop.type not in STRING_TYPES:
        issues.append(
            _issue(
                "PROPERTY_PATTERN_INVALID_TYPE",
                "pattern applies only to string-like fields.",
                f"{path}.pattern",
            )
        )
    if (prop.minimum is not None or prop.maximum is not None) and prop.type not in NUMERIC_TYPES:
        issues.append(
            _issue(
                "PROPERTY_NUMERIC_LIMIT_INVALID_TYPE",
                "minimum and maximum apply only to numeric fields.",
                path,
            )
        )
    if (
        (prop.min_length is not None or prop.max_length is not None)
        and prop.type not in STRING_TYPES
        and prop.type != "array"
    ):
        issues.append(
            _issue(
                "PROPERTY_LENGTH_INVALID_TYPE",
                "length constraints apply only to strings or arrays.",
                path,
            )
        )
    if prop.items is not None and prop.type != "array":
        issues.append(
            _issue(
                "PROPERTY_ITEMS_INVALID_TYPE",
                "items applies only to array fields.",
                f"{path}.items",
            )
        )
    if prop.type == "array" and prop.items is None:
        issues.append(
            _issue(
                "PROPERTY_ARRAY_ITEMS_REQUIRED",
                "array fields must declare an item type.",
                f"{path}.items",
            )
        )
    if prop.target is not None and prop.type != "reference":
        issues.append(
            _issue(
                "PROPERTY_TARGET_INVALID_TYPE",
                "target applies only to reference fields.",
                f"{path}.target",
            )
        )
    if prop.type == "reference" and not prop.target:
        issues.append(
            _issue(
                "PROPERTY_REFERENCE_TARGET_REQUIRED",
                "reference fields must declare a target entity.",
                f"{path}.target",
            )
        )
    if (
        prop.minimum is not None
        and prop.maximum is not None
        and Decimal(str(prop.minimum)) > Decimal(str(prop.maximum))
    ):
        issues.append(
            _issue("PROPERTY_LIMIT_RANGE_INVALID", "minimum cannot exceed maximum.", path)
        )
    if (
        prop.min_length is not None
        and prop.max_length is not None
        and prop.min_length > prop.max_length
    ):
        issues.append(
            _issue("PROPERTY_LENGTH_RANGE_INVALID", "min_length cannot exceed max_length.", path)
        )
    if prop.default is not None and not value_matches_type(prop.default, prop.type):
        issues.append(
            _issue(
                "PROPERTY_DEFAULT_TYPE_INVALID",
                "default value does not match declared type.",
                f"{path}.default",
            )
        )
    if prop.enum is not None:
        for index, value in enumerate(prop.enum):
            if not value_matches_type(value, prop.type):
                issues.append(
                    _issue(
                        "PROPERTY_ENUM_TYPE_INVALID",
                        "enum value does not match declared type.",
                        f"{path}.enum[{index}]",
                    )
                )
        if prop.default is not None and prop.default not in prop.enum:
            issues.append(
                _issue(
                    "PROPERTY_DEFAULT_NOT_IN_ENUM",
                    "default value must be one of the enum values.",
                    f"{path}.default",
                )
            )
    return issues
