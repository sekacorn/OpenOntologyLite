"""JSON Schema exporter."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from open_ontology_lite.models import Ontology, PropertyDef


def _property_schema(prop: PropertyDef) -> dict[str, Any]:
    if prop.type == "reference":
        schema: dict[str, Any] = {"$ref": f"#/$defs/{prop.target}"}
    elif prop.type == "array":
        schema = {"type": "array", "items": {"type": prop.items or "string"}}
    elif prop.type == "object":
        schema = {"type": "object", "additionalProperties": True}
    elif prop.type == "integer":
        schema = {"type": "integer"}
    elif prop.type in {"number", "decimal"}:
        schema = {"type": "number"}
    elif prop.type == "boolean":
        schema = {"type": "boolean"}
    else:
        schema = {"type": "string"}
        if prop.type == "date":
            schema["format"] = "date"
        elif prop.type == "datetime":
            schema["format"] = "date-time"
        elif prop.type == "uuid":
            schema["format"] = "uuid"
    if prop.nullable:
        if "$ref" in schema:
            schema = {"anyOf": [schema, {"type": "null"}]}
        elif "type" in schema:
            schema["type"] = [schema["type"], "null"]
    if prop.description:
        schema["description"] = prop.description
    if prop.enum is not None:
        schema["enum"] = list(prop.enum)
    if prop.pattern:
        schema["pattern"] = prop.pattern
    if prop.minimum is not None:
        schema["minimum"] = float(prop.minimum)
    if prop.maximum is not None:
        schema["maximum"] = float(prop.maximum)
    if prop.min_length is not None:
        key = "minItems" if prop.type == "array" else "minLength"
        schema[key] = prop.min_length
    if prop.max_length is not None:
        key = "maxItems" if prop.type == "array" else "maxLength"
        schema[key] = prop.max_length
    if prop.default is not None:
        schema["default"] = prop.default
    return schema


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def entity_schema(ontology: Ontology, entity_name: str) -> dict[str, Any]:
    """Export one entity as JSON Schema."""

    entity = ontology.entities[entity_name]
    properties = {
        name: _property_schema(entity.properties[name]) for name in sorted(entity.properties)
    }
    required = sorted(name for name, prop in entity.properties.items() if prop.required)
    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{ontology.ontology.namespace}.{entity_name}",
        "title": entity.name or entity_name,
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }
    if entity.description:
        schema["description"] = entity.description
    if required:
        schema["required"] = required
    return schema


def combined_schema(ontology: Ontology, entity: str | None = None) -> dict[str, Any]:
    """Export one entity or a combined schema document."""

    defs = {name: entity_schema(ontology, name) for name in sorted(ontology.entities)}
    if entity:
        schema = entity_schema(ontology, entity)
        schema["$defs"] = defs
        return schema
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": ontology.ontology.namespace,
        "title": ontology.ontology.name,
        "description": ontology.ontology.description,
        "$defs": defs,
    }


def json_schema_text(ontology: Ontology, entity: str | None = None) -> str:
    """Return deterministic JSON Schema text."""

    return (
        json.dumps(
            combined_schema(ontology, entity), sort_keys=True, indent=2, default=_json_default
        )
        + "\n"
    )
