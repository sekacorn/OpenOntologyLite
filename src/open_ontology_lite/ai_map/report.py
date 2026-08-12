"""Deterministic Markdown reporting for AI System Maps."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from open_ontology_lite.ai_map.loading import ai_system_map_digest
from open_ontology_lite.ai_map.models import AISystemMap
from open_ontology_lite.ai_map.validation import (
    AISystemMapValidationResult,
    validate_ai_system_map,
)
from open_ontology_lite.exporters.escaping import markdown
from open_ontology_lite.version import __version__


def _joined(values: tuple[str, ...]) -> str:
    return ", ".join(markdown(value) for value in values) or "None"


def ai_system_map_report(
    ai_map: AISystemMap,
    *,
    validation: AISystemMapValidationResult | None = None,
    source: str | Path | None = None,
) -> str:
    """Generate a deterministic, operator-focused Markdown report."""

    validation = validation or validate_ai_system_map(ai_map)
    risk_counts = Counter(task.risk_level for task in ai_map.tasks)
    route_counts = Counter(route for task in ai_map.tasks for route in task.allowed_routes)
    lines = [
        "# AI System Map Report",
        "",
        "## Executive Summary",
        "",
        (
            "This map defines the meaning, risk, allowed routing, human-review "
            "requirements, audit expectations, and cost/outcome measurement "
            f"expectations for {markdown(ai_map.system.name)}."
        ),
        "",
        f"- Purpose: {markdown(ai_map.system.purpose or 'Not specified')}",
        f"- System risk profile: {markdown(ai_map.system.risk_profile)}",
        f"- Environment: {markdown(ai_map.system.environment)}",
        f"- Tasks: {len(ai_map.tasks)}",
        f"- Entities: {len(ai_map.entities)}",
        f"- Validation errors: {len(validation.errors)}",
        f"- Validation warnings: {len(validation.warnings)}",
        "",
        "## System",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Name | {markdown(ai_map.system.name)} |",
        f"| Purpose | {markdown(ai_map.system.purpose or 'Not specified')} |",
        f"| Owner label | {markdown(ai_map.system.owner_label or 'Not specified')} |",
        f"| Risk profile | {markdown(ai_map.system.risk_profile)} |",
        f"| Environment | {markdown(ai_map.system.environment)} |",
        f"| Notes | {markdown(ai_map.system.notes or 'None')} |",
        "",
        "## Business Entities",
        "",
        "| Entity | Sensitivity | Description | Fields |",
        "| --- | --- | --- | --- |",
    ]
    for entity in ai_map.entities:
        lines.append(
            f"| {markdown(entity.name)} | {markdown(entity.sensitivity)} | "
            f"{markdown(entity.description or 'Not specified')} | {_joined(entity.fields)} |"
        )
    if not ai_map.entities:
        lines.append("| None | - | - | - |")

    lines.extend(
        [
            "",
            "## AI Tasks",
            "",
            "| Task | Category | Risk | Customer-facing | Allowed routes | Escalation |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for task in ai_map.tasks:
        lines.append(
            f"| {markdown(task.name)} | {markdown(task.category)} | "
            f"{markdown(task.risk_level)} | {'yes' if task.customer_facing else 'no'} | "
            f"{_joined(task.allowed_routes)} | {_joined(task.escalation)} |"
        )
    if not ai_map.tasks:
        lines.append("| None | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Data, Models, and Tool Boundaries",
            "",
            "| Task | Data sources | Retrieval boundaries | Models | Tool access |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for task in ai_map.tasks:
        lines.append(
            f"| {markdown(task.name)} | {_joined(task.data_sources)} | "
            f"{_joined(task.retrieval_boundaries)} | {_joined(task.models)} | "
            f"{_joined(task.tool_access)} |"
        )
    if not ai_map.tasks:
        lines.append("| None | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Deployment and Data Handling",
            "",
            "| Task | Data handling | Retention | Deployment restrictions | Geography |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for task in ai_map.tasks:
        lines.append(
            f"| {markdown(task.name)} | {_joined(task.data_handling_expectations)} | "
            f"{markdown(task.data_retention or 'Not specified')} | "
            f"{_joined(task.deployment_restrictions)} | "
            f"{_joined(task.geographic_restrictions)} |"
        )
    if not ai_map.tasks:
        lines.append("| None | - | - | - | - |")

    lines.extend(["", "## Risk Summary", ""])
    for risk in sorted(risk_counts):
        lines.append(f"- {markdown(risk)}: {risk_counts[risk]}")
    if not risk_counts:
        lines.append("- No tasks declared.")

    lines.extend(["", "## Model Route Summary", ""])
    for route in sorted(route_counts):
        lines.append(f"- {markdown(route)}: {route_counts[route]}")
    if not route_counts:
        lines.append("- No routes used.")

    lines.extend(["", "## Human Review and Escalation", ""])
    controlled_tasks = [
        task for task in ai_map.tasks if task.human_review_required or task.escalation
    ]
    if controlled_tasks:
        for task in controlled_tasks:
            review = "required" if task.human_review_required else "not required"
            lines.append(
                f"- **{markdown(task.name)}**: human review {review}; "
                f"escalation: {_joined(task.escalation)}"
            )
    else:
        lines.append("- No task declares mandatory human review.")

    lines.extend(
        [
            "",
            "## Audit Expectations",
            "",
            "| Task | Required | Expected events |",
            "| --- | --- | --- |",
        ]
    )
    for task in ai_map.tasks:
        lines.append(
            f"| {markdown(task.name)} | {'yes' if task.audit_required else 'no'} | "
            f"{_joined(task.expected_audit_events)} |"
        )

    lines.extend(
        [
            "",
            "## Cost and Outcome Measurement Expectations",
            "",
            "| Task | Required | Expected metrics |",
            "| --- | --- | --- |",
        ]
    )
    for task in ai_map.tasks:
        lines.append(
            f"| {markdown(task.name)} | "
            f"{'yes' if task.cost_tracking_required else 'no'} | "
            f"{_joined(task.expected_metrics)} |"
        )

    lines.extend(
        [
            "",
            "## Linux of AI Integration Map",
            "",
            "| Tool | Mode | Portable meaning |",
            "| --- | --- | --- |",
        ]
    )
    for integration in ai_map.integrations:
        lines.append(
            f"| {markdown(integration.tool)} | {markdown(integration.mode)} | "
            f"{markdown(integration.meaning)} |"
        )
    if not ai_map.integrations:
        lines.append("| None | - | No integrations declared. |")

    lines.extend(["", "## Warnings", ""])
    if validation.warnings:
        for issue in validation.warnings:
            lines.append(
                f"- {markdown(issue.code)} at {markdown(issue.path)}: {markdown(issue.message)}"
            )
    else:
        lines.append("- No validation warnings.")

    lines.extend(["", "## Limitations", ""])
    for limitation in ai_map.limitations:
        lines.append(f"- {markdown(limitation)}")
    if not ai_map.limitations:
        lines.append("- No limitations were documented.")

    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            f"- Schema version: {markdown(ai_map.schema_version)}",
            f"- OpenOntologyLite version: {markdown(__version__)}",
            f"- Canonical SHA-256: {ai_system_map_digest(ai_map)}",
            "- The digest identifies canonical map content only; it is not a signature, "
            "endorsement, proof of provenance, or evidence that declared controls operate.",
        ]
    )
    if source is not None:
        lines.append(f"- Source: {markdown(source)}")
    lines.append("")
    return "\n".join(lines)
