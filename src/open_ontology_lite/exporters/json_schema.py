"""JSON Schema exporter."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

from open_ontology_lite.errors import OntologyExportError
from open_ontology_lite.models import ActionDef, Ontology, PropertyDef
from open_ontology_lite.normalization import ontology_digest


def _action(ontology: Ontology, action: ActionDef | str) -> ActionDef:
    if isinstance(action, ActionDef):
        return action
    matches = [item for item in ontology.actions if item.name == action or action in item.aliases]
    if len(matches) != 1:
        raise KeyError(f"Unknown or ambiguous action: {action}")
    return matches[0]


def _json_number(value: int | float | Decimal) -> int | float:
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal) and value == value.to_integral_value():
        return int(value)
    result = float(value)
    if not math.isfinite(result):
        raise OntologyExportError("A numeric constraint cannot be represented as finite JSON.")
    return result


def property_schema(prop: PropertyDef) -> dict[str, Any]:
    """Convert a property definition to bounded JSON Schema 2020-12 vocabulary."""

    if prop.type == "reference":
        choices: list[dict[str, Any]] = [
            {"type": "string", "minLength": 1},
            {"type": "integer"},
        ]
        choices.append({"$ref": f"#/$defs/{prop.target}"} if prop.target else {"type": "object"})
        schema: dict[str, Any] = {"anyOf": choices}
    elif prop.type == "array":
        item = prop.items_schema or PropertyDef(type=prop.items or "string")
        schema = {"type": "array", "items": property_schema(item)}
    elif prop.type == "object":
        nested = {name: property_schema(prop.properties[name]) for name in sorted(prop.properties)}
        schema = {
            "type": "object",
            "additionalProperties": not bool(prop.properties),
            "properties": nested,
        }
        required = sorted(name for name, item in prop.properties.items() if item.required)
        if required:
            schema["required"] = required
    elif prop.type == "integer":
        schema = {"type": "integer"}
    elif prop.type == "number":
        schema = {"type": "number"}
    elif prop.type == "decimal":
        schema = {
            "anyOf": [
                {"type": "integer"},
                {
                    "type": "string",
                    "pattern": (
                        r"^\s*-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
                        r"(?:[eE][+-]?[0-9]+)?\s*$"
                    ),
                },
            ],
            "x-exact-decimal": True,
        }
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
        elif "anyOf" in schema:
            schema["anyOf"].append({"type": "null"})
    if prop.description:
        schema["description"] = prop.description
    if prop.enum is not None:
        schema["enum"] = list(prop.enum)
    if prop.pattern:
        schema["pattern"] = prop.pattern
    if prop.minimum is not None:
        key = "x-minimum" if prop.type == "decimal" else "minimum"
        schema[key] = str(prop.minimum) if prop.type == "decimal" else _json_number(prop.minimum)
    if prop.maximum is not None:
        key = "x-maximum" if prop.type == "decimal" else "maximum"
        schema[key] = str(prop.maximum) if prop.type == "decimal" else _json_number(prop.maximum)
    if prop.min_length is not None:
        key = "minItems" if prop.type == "array" else "minLength"
        schema[key] = prop.min_length
    if prop.max_length is not None:
        key = "maxItems" if prop.type == "array" else "maxLength"
        schema[key] = prop.max_length
    if "default" in prop.model_fields_set:
        schema["default"] = prop.default
    return schema


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise OntologyExportError("JSON Schema contains a non-finite decimal value.")
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def entity_schema(ontology: Ontology, entity_name: str) -> dict[str, Any]:
    """Export one entity as JSON Schema."""

    entity = ontology.entities[entity_name]
    properties = {
        name: property_schema(entity.properties[name]) for name in sorted(entity.properties)
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


def action_input_schema(ontology: Ontology, action: ActionDef | str) -> dict[str, Any]:
    """Export one action's inputs as a deterministic JSON Schema document."""

    contract = _action(ontology, action)
    properties = {name: property_schema(contract.inputs[name]) for name in sorted(contract.inputs)}
    required = sorted(name for name, item in contract.inputs.items() if item.required)
    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{ontology.ontology.namespace}.actions.{contract.name}.inputs",
        "title": f"{contract.name} inputs",
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "$defs": {name: entity_schema(ontology, name) for name in sorted(ontology.entities)},
        "x-ontology": {
            "id": ontology.ontology.id,
            "version": ontology.ontology.version,
            "namespace": ontology.ontology.namespace,
            "digest": ontology_digest(ontology),
        },
    }
    if contract.description:
        schema["description"] = contract.description
    if required:
        schema["required"] = required
    return schema


def action_output_schema(ontology: Ontology, action: ActionDef | str) -> dict[str, Any] | None:
    """Export one action's output contract when it is representable."""

    contract = _action(ontology, action)
    if contract.output is None:
        return None
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{ontology.ontology.namespace}.actions.{contract.name}.output",
        **property_schema(contract.output),
        "$defs": {name: entity_schema(ontology, name) for name in sorted(ontology.entities)},
        "x-ontology": {
            "id": ontology.ontology.id,
            "version": ontology.ontology.version,
            "namespace": ontology.ontology.namespace,
            "digest": ontology_digest(ontology),
        },
    }


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
            combined_schema(ontology, entity),
            sort_keys=True,
            indent=2,
            default=_json_default,
            allow_nan=False,
        )
        + "\n"
    )
