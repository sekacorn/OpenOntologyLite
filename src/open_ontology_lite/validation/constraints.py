"""Property constraint validation."""

from __future__ import annotations

import math
import re
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
        return (
            isinstance(value, (int, float, Decimal))
            and not isinstance(value, bool)
            and (not isinstance(value, float) or math.isfinite(value))
            and (not isinstance(value, Decimal) or value.is_finite())
        )
    if property_type == "decimal":
        try:
            candidate = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return False
        return not isinstance(value, bool) and candidate.is_finite()
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
    if prop.items_schema is not None and prop.type != "array":
        issues.append(
            _issue(
                "PROPERTY_ITEMS_SCHEMA_INVALID_TYPE",
                "items_schema applies only to array fields.",
                f"{path}.items_schema",
            )
        )
    if prop.items is not None and prop.items_schema is not None:
        issues.append(
            _issue(
                "PROPERTY_ARRAY_ITEMS_AMBIGUOUS",
                "array fields must use items or items_schema, not both.",
                path,
            )
        )
    if prop.type == "array" and prop.items is None and prop.items_schema is None:
        issues.append(
            _issue(
                "PROPERTY_ARRAY_ITEMS_REQUIRED",
                "array fields must declare an item type.",
                f"{path}.items",
            )
        )
    if prop.properties and prop.type != "object":
        issues.append(
            _issue(
                "PROPERTY_NESTED_PROPERTIES_INVALID_TYPE",
                "properties applies only to object fields.",
                f"{path}.properties",
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
    for name, limit in (("minimum", prop.minimum), ("maximum", prop.maximum)):
        if (isinstance(limit, float) and not math.isfinite(limit)) or (
            isinstance(limit, Decimal) and not limit.is_finite()
        ):
            issues.append(
                _issue(
                    "PROPERTY_NUMERIC_LIMIT_NON_FINITE",
                    f"{name} must be finite.",
                    f"{path}.{name}",
                )
            )
    has_default = "default" in prop.model_fields_set
    default_valid = True
    if has_default:
        default_valid = (
            prop.nullable if prop.default is None else value_matches_type(prop.default, prop.type)
        )
    if has_default and not default_valid:
        issues.append(
            _issue(
                "PROPERTY_DEFAULT_TYPE_INVALID",
                "default value does not match declared type.",
                f"{path}.default",
            )
        )
    if prop.enum is not None:
        for index, value in enumerate(prop.enum):
            enum_valid = (
                value is None and prop.nullable
                if value is None
                else value_matches_type(value, prop.type)
            )
            if not enum_valid:
                issues.append(
                    _issue(
                        "PROPERTY_ENUM_TYPE_INVALID",
                        "enum value does not match declared type.",
                        f"{path}.enum[{index}]",
                    )
                )
        if has_default and prop.default not in prop.enum:
            issues.append(
                _issue(
                    "PROPERTY_DEFAULT_NOT_IN_ENUM",
                    "default value must be one of the enum values.",
                    f"{path}.default",
                )
            )
    if prop.pattern is not None:
        try:
            re.compile(prop.pattern)
        except re.error:
            issues.append(
                _issue(
                    "PROPERTY_PATTERN_INVALID",
                    "pattern is not a valid regular expression.",
                    f"{path}.pattern",
                )
            )
    return issues
