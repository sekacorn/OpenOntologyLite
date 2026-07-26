"""Cycle analysis for ontology references."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from open_ontology_lite.models import Ontology


class Cycle(BaseModel):
    """A detected graph cycle."""

    model_config = ConfigDict(frozen=True)

    path: tuple[str, ...]
    classification: str
    reason: str


def build_graph(ontology: Ontology) -> dict[str, set[str]]:
    """Build an entity graph from relationships and reference properties."""

    graph: dict[str, set[str]] = {name: set() for name in ontology.entities}
    for rel in ontology.relationships:
        graph.setdefault(rel.from_, set()).add(rel.to)
    for entity_name, entity in ontology.entities.items():
        for prop in entity.properties.values():
            if prop.type == "reference" and prop.target:
                graph.setdefault(entity_name, set()).add(prop.target)
    return graph


def find_cycles(ontology: Ontology) -> tuple[Cycle, ...]:
    """Detect cycles without rejecting them by default."""

    graph = build_graph(ontology)
    cycles: set[tuple[str, ...]] = set()
    stack: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        visiting.add(node)
        stack.append(node)
        for neighbor in sorted(graph.get(node, set())):
            if neighbor not in graph:
                continue
            if neighbor in visiting:
                start = stack.index(neighbor)
                cycle = (*stack[start:], neighbor)
                # Normalize rotations so the same cycle discovered from a
                # different start node is reported only once.
                rotations = [cycle[i:-1] + cycle[:i] + (cycle[i],) for i in range(len(cycle) - 1)]
                cycles.add(min(rotations))
            elif neighbor not in visited:
                visit(neighbor)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for entity in sorted(graph):
        if entity not in visited:
            visit(entity)
    return tuple(
        Cycle(
            path=cycle,
            classification="potentially_problematic" if len(cycle) == 2 else "informational",
            reason=(
                "Relationship and reference cycles are allowed in this alpha "
                "but may affect downstream tools."
            ),
        )
        for cycle in sorted(cycles)
    )
