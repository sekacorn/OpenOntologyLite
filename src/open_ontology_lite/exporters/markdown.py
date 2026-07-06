"""Markdown documentation exporter."""

from __future__ import annotations

from datetime import UTC, datetime

from open_ontology_lite.exporters.escaping import markdown
from open_ontology_lite.models import Ontology, ValidationReport
from open_ontology_lite.normalization import ontology_digest


def markdown_docs(
    ontology: Ontology,
    *,
    validation: ValidationReport | None = None,
    include_timestamp: bool = False,
) -> str:
    """Generate deterministic Markdown documentation."""

    report = validation or ValidationReport()
    lines = [
        f"# {markdown(ontology.ontology.name)}",
        "",
        "## Overview",
        "",
        f"- ID: `{markdown(ontology.ontology.id)}`",
        f"- Version: `{markdown(ontology.ontology.version)}`",
        f"- Namespace: `{markdown(ontology.ontology.namespace)}`",
        f"- Digest: `{ontology_digest(ontology)}`",
        f"- Validation errors: {len(report.errors)}",
        f"- Validation warnings: {len(report.warnings)}",
    ]
    if ontology.ontology.description:
        lines.extend(["", markdown(ontology.ontology.description)])
    if include_timestamp:
        lines.extend(["", f"Generated: {datetime.now(UTC).isoformat()}"])
    lines.extend(
        ["", "## Entity Index", "", "| Entity | Properties | Description |", "|---|---:|---|"]
    )
    for name in sorted(ontology.entities):
        entity = ontology.entities[name]
        lines.append(
            f"| `{markdown(name)}` | {len(entity.properties)} | {markdown(entity.description)} |"
        )
    lines.extend(["", "## Entities"])
    for name in sorted(ontology.entities):
        entity = ontology.entities[name]
        lines.extend(["", f"### {markdown(name)}", "", markdown(entity.description), ""])
        lines.extend(["| Property | Type | Required | Constraints |", "|---|---|---:|---|"])
        for prop_name in sorted(entity.properties):
            prop = entity.properties[prop_name]
            constraints = []
            if prop.enum is not None:
                constraints.append("enum=" + ", ".join(markdown(v) for v in prop.enum))
            if prop.target:
                constraints.append(f"target={markdown(prop.target)}")
            if prop.minimum is not None:
                constraints.append(f"min={prop.minimum}")
            if prop.maximum is not None:
                constraints.append(f"max={prop.maximum}")
            constraint_text = markdown("; ".join(constraints))
            lines.append(
                f"| `{markdown(prop_name)}` | `{prop.type}` | "
                f"{prop.required} | {constraint_text} |"
            )
    lines.extend(
        [
            "",
            "## Relationships",
            "",
            "| Name | From | To | Cardinality | Required |",
            "|---|---|---|---|---:|",
        ]
    )
    for rel in sorted(ontology.relationships, key=lambda item: item.name):
        lines.append(
            f"| `{markdown(rel.name)}` | `{markdown(rel.from_)}` | "
            f"`{markdown(rel.to)}` | `{rel.cardinality}` | {rel.required} |"
        )
    lines.extend(
        [
            "",
            "## Actions",
            "",
            "| Name | Subject | Permissions | Preconditions |",
            "|---|---|---|---:|",
        ]
    )
    for action in sorted(ontology.actions, key=lambda item: item.name):
        permissions = markdown(", ".join(action.permissions))
        lines.append(
            f"| `{markdown(action.name)}` | `{markdown(action.subject)}` | "
            f"{permissions} | {len(action.preconditions)} |"
        )
    lines.extend(["", "## Permissions", "", "| Permission | Risk | Description |", "|---|---|---|"])
    for name in sorted(ontology.permissions):
        perm = ontology.permissions[name]
        lines.append(f"| `{markdown(name)}` | `{perm.risk}` | {markdown(perm.description)} |")
    lines.extend(["", "## Validation Summary", ""])
    if not report.issues:
        lines.append("No validation issues.")
    else:
        lines.extend(["| Severity | Code | Path | Message |", "|---|---|---|---|"])
        for issue in report.issues:
            message = markdown(issue.message)
            lines.append(
                f"| `{issue.severity}` | `{issue.code}` | "
                f"`{markdown(issue.path)}` | {message} |"
            )
    return "\n".join(lines) + "\n"
