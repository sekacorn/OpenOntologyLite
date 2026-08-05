"""Mermaid rendering for AI System Maps."""

from __future__ import annotations

from open_ontology_lite.ai_map.models import AISystemMap
from open_ontology_lite.exporters.escaping import mermaid


def ai_system_map_mermaid(ai_map: AISystemMap) -> str:
    """Render a deterministic Mermaid flowchart with safe identifiers."""

    lines = [
        "flowchart TD",
        f'  system["AI System: {mermaid(ai_map.system.name)}"]',
    ]
    entity_ids: dict[str, str] = {}
    task_node_ids: list[str] = []
    route_ids: dict[str, str] = {}
    escalation_ids: dict[str, str] = {}

    for index, entity in enumerate(ai_map.entities, start=1):
        node_id = f"entity_{index:04d}"
        entity_ids[entity.name] = node_id
        lines.append(
            f'  {node_id}["Entity: {mermaid(entity.name)}<br/>'
            f'Sensitivity: {mermaid(entity.sensitivity)}"]'
        )
        lines.append(f"  system --> {node_id}")

    for index, task in enumerate(ai_map.tasks, start=1):
        node_id = f"task_{index:04d}"
        task_node_ids.append(node_id)
        review = "<br/>Review: required" if task.human_review_required else ""
        lines.append(
            f'  {node_id}["Task: {mermaid(task.name)}<br/>'
            f'Risk: {mermaid(task.risk_level)}{review}"]'
        )
        lines.append(f"  system --> {node_id}")

    for index, route in enumerate(ai_map.model_routes, start=1):
        node_id = f"route_{index:04d}"
        route_ids[route.name] = node_id
        lines.append(f'  {node_id}(["Route: {mermaid(route.name)}"])')

    for index, escalation in enumerate(ai_map.escalation_paths, start=1):
        node_id = f"escalation_{index:04d}"
        escalation_ids[escalation.name] = node_id
        lines.append(f'  {node_id}{{"Escalation: {mermaid(escalation.name)}"}}')

    uses_audit = any(task.audit_required for task in ai_map.tasks)
    uses_cost = any(task.cost_tracking_required for task in ai_map.tasks)
    if uses_audit:
        lines.append('  audit[["Audit events"]]')
    if uses_cost:
        lines.append('  cost[["Cost/outcome metrics"]]')

    for task, task_id in zip(ai_map.tasks, task_node_ids, strict=True):
        for entity_name in task.related_entities:
            if entity_name in entity_ids:
                lines.append(f"  {task_id} -->|reads or produces| {entity_ids[entity_name]}")
        for route_name in task.allowed_routes:
            if route_name in route_ids:
                lines.append(f"  {task_id} -->|allowed| {route_ids[route_name]}")
        for escalation_name in task.escalation:
            if escalation_name in escalation_ids:
                lines.append(f"  {task_id} -->|escalates| {escalation_ids[escalation_name]}")
        if task.audit_required:
            lines.append(f"  {task_id} -.->|records| audit")
        if task.cost_tracking_required:
            lines.append(f"  {task_id} -.->|measures| cost")

    return "\n".join(lines) + "\n"
