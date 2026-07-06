"""Canonical deterministic ontology serialization."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any, cast

from open_ontology_lite.models import Ontology


def _stable(value: Any) -> Any:
    # Decimal is stringified so canonical JSON does not depend on float
    # conversion or platform-specific representation details.
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple | list):
        return [_stable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
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
    return cast(dict[str, Any], _stable(data))


def canonical_json(ontology: Ontology) -> str:
    """Return stable canonical JSON with a trailing newline."""

    return json.dumps(normalize_ontology(ontology), sort_keys=True, separators=(",", ":")) + "\n"


def ontology_digest(ontology: Ontology) -> str:
    """Return the SHA-256 digest of the canonical representation."""

    return hashlib.sha256(canonical_json(ontology).encode("utf-8")).hexdigest()
