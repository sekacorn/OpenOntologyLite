"""Mermaid exporter."""

from __future__ import annotations

from open_ontology_lite.exporters.escaping import mermaid
from open_ontology_lite.models import Ontology

CARDINALITY = {
    "one_to_one": "||--||",
    "one_to_many": "||--o{",
    "many_to_one": "}o--||",
    "many_to_many": "}o--o{",
}


def mermaid_text(
    ontology: Ontology, *, detailed: bool = False, include_actions: bool = False
) -> str:
    """Return deterministic Mermaid class diagram source."""

    lines = ["classDiagram"]
    for name in sorted(ontology.entities):
        entity = ontology.entities[name]
        lines.append(f"  class {name} {{")
        if detailed:
            for prop_name in sorted(entity.properties):
                prop = entity.properties[prop_name]
                marker = "*" if prop.required else ""
                lines.append(f"    {mermaid(prop.type)} {mermaid(prop_name)}{marker}")
        lines.append("  }")
    for rel in sorted(ontology.relationships, key=lambda item: item.name):
        label = mermaid(rel.name)
        lines.append(f'  {rel.from_} {CARDINALITY[rel.cardinality]} {rel.to} : "{label}"')
    if include_actions:
        for action in sorted(ontology.actions, key=lambda item: item.name):
            lines.append(f"  {action.subject} : action {mermaid(action.name)}()")
    return "\n".join(lines) + "\n"
