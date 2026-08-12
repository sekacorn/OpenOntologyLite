"""Canonical deterministic ontology serialization."""

from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import Any, cast

from open_ontology_lite.errors import UnsafeInputError
from open_ontology_lite.models import Ontology

_UNORDERED_DECLARATION_FIELDS = frozenset(
    {
        "aliases",
        "expected_audit_events",
        "escalation",
        "permissions",
        "tags",
    }
)


def _stable(value: Any) -> Any:
    # Decimal is stringified so canonical JSON does not depend on float
    # conversion or platform-specific representation details.
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise UnsafeInputError("Canonical data contains a non-finite decimal value.")
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        raise UnsafeInputError("Canonical data contains a non-finite numeric value.")
    if isinstance(value, tuple | list):
        return [_stable(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise UnsafeInputError("Canonical mappings require string keys.")
        return {key: _stable(value[key]) for key in sorted(value)}
    return value


def _canonical_declarations(value: Any, *, metadata: bool = False) -> Any:
    """Normalize declaration fields that have set-like contract semantics.

    Their source order does not affect validation, action-contract checks, or
    generated neutral contracts. Keeping their order out of the digest makes
    locks reproducible across formatter-only rewrites without changing ordered
    values such as enum alternatives and declarative preconditions.
    """

    if isinstance(value, dict):
        normalized = {
            key: _canonical_declarations(item, metadata=metadata or key == "metadata")
            for key, item in value.items()
        }
        if not metadata:
            for key in _UNORDERED_DECLARATION_FIELDS:
                item = normalized.get(key)
                if isinstance(item, list) and all(isinstance(entry, str) for entry in item):
                    normalized[key] = sorted(item)
        return normalized
    if isinstance(value, list):
        return [_canonical_declarations(item, metadata=metadata) for item in value]
    return value


def normalize_ontology(ontology: Ontology) -> dict[str, Any]:
    """Return a deterministic normalized representation."""

    data = ontology.model_dump(by_alias=True, exclude_none=True)
    # Sort every map-like declaration by stable identifier; list-backed
    # declarations are sorted below by their explicit names.
    data["entities"] = {
        entity_name: _stable(data["entities"][entity_name])
        for entity_name in sorted(data.get("entities", {}))
    }
    for entity in data["entities"].values():
        if "properties" in entity:
            entity["properties"] = {
                prop_name: _stable(entity["properties"][prop_name])
                for prop_name in sorted(entity["properties"])
            }
    data["relationships"] = sorted(
        (_stable(rel) for rel in data.get("relationships", [])),
        key=lambda item: str(item.get("name", "")),
    )
    data["actions"] = sorted(
        (_stable(action) for action in data.get("actions", [])),
        key=lambda item: str(item.get("name", "")),
    )
    for action in data["actions"]:
        if "inputs" in action:
            action["inputs"] = {
                name: _stable(action["inputs"][name]) for name in sorted(action["inputs"])
            }
    data["permissions"] = {
        name: _stable(data["permissions"][name]) for name in sorted(data.get("permissions", {}))
    }
    return cast(dict[str, Any], _canonical_declarations(_stable(data)))


def canonical_json(ontology: Ontology) -> str:
    """Return stable canonical JSON with a trailing newline."""

    return (
        json.dumps(
            normalize_ontology(ontology),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


def ontology_digest(ontology: Ontology) -> str:
    """Return the SHA-256 digest of the canonical representation."""

    return hashlib.sha256(canonical_json(ontology).encode("utf-8")).hexdigest()
