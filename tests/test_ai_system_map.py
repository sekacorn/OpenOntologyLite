import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from open_ontology_lite import (
    ai_system_map_digest,
    ai_system_map_mermaid,
    ai_system_map_report,
    load_ai_system_map,
    validate_ai_system_map,
)
from open_ontology_lite.cli import app
from open_ontology_lite.errors import OntologyParseError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "ai_system_map" / "customer_support_ai.yaml"
runner = CliRunner()


def test_customer_support_ai_map_is_valid_and_complete() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    result = validate_ai_system_map(ai_map)
    assert result.valid
    assert not result.warnings
    assert len(ai_map.tasks) == 10
    assert {task.name for task in ai_map.tasks} == {
        "PasswordReset",
        "InternalSummary",
        "BillingFAQ",
        "RefundRequest",
        "AccountCancellation",
        "AngryCustomerEscalation",
        "SecurityConcern",
        "LegalQuestion",
        "MedicalQuestion",
        "FinancialQuestion",
    }


def test_ai_map_digest_and_outputs_are_deterministic() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    outputs = (
        ai_system_map_digest(ai_map),
        ai_system_map_report(ai_map),
        ai_system_map_mermaid(ai_map),
    )
    assert outputs == (
        ai_system_map_digest(ai_map),
        ai_system_map_report(ai_map),
        ai_system_map_mermaid(ai_map),
    )
    assert "## Reproducibility" in outputs[1]
    assert "flowchart TD" in outputs[2]


def test_missing_task_name_fails_validation() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    bad_task = ai_map.tasks[0].model_copy(update={"name": ""})
    result = validate_ai_system_map(ai_map.model_copy(update={"tasks": (bad_task,)}))
    assert "TASK_NAME_REQUIRED" in {issue.code for issue in result.errors}


def test_invalid_route_fails_validation() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    bad_task = ai_map.tasks[0].model_copy(update={"allowed_routes": ("untrusted_route",)})
    result = validate_ai_system_map(ai_map.model_copy(update={"tasks": (bad_task,)}))
    assert "INVALID_TASK_ROUTE" in {issue.code for issue in result.errors}


def test_unknown_related_entity_fails_validation() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    bad_task = ai_map.tasks[0].model_copy(update={"related_entities": ("MissingEntity",)})
    result = validate_ai_system_map(ai_map.model_copy(update={"tasks": (bad_task,)}))
    assert "UNKNOWN_RELATED_ENTITY" in {issue.code for issue in result.errors}


def test_validation_caps_repeated_diagnostics() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    bad_task = ai_map.tasks[0].model_copy(
        update={"related_entities": tuple(f"Missing{index}" for index in range(1_100))}
    )
    result = validate_ai_system_map(ai_map.model_copy(update={"tasks": (bad_task,)}))
    assert len(result.issues) == 1_001
    assert result.issues[-1].code == "VALIDATION_ISSUE_LIMIT"


def test_high_risk_candidate_route_warns_without_review_or_justification() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    bad_task = ai_map.tasks[0].model_copy(
        update={
            "risk_level": "high",
            "allowed_routes": ("candidate_model",),
            "human_review_required": False,
            "candidate_route_justification": None,
        }
    )
    result = validate_ai_system_map(ai_map.model_copy(update={"tasks": (bad_task,)}))
    assert "HIGH_RISK_CANDIDATE_ROUTE" in {issue.code for issue in result.warnings}


def test_unknown_task_risk_produces_warning() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    unknown_task = ai_map.tasks[0].model_copy(update={"risk_level": "unknown"})
    result = validate_ai_system_map(ai_map.model_copy(update={"tasks": (unknown_task,)}))
    assert result.valid
    assert "UNKNOWN_TASK_RISK" in {issue.code for issue in result.warnings}


def test_sensitive_task_requires_review_blocking_or_escalation() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    bad_task = ai_map.tasks[0].model_copy(
        update={
            "category": "legal",
            "allowed_routes": ("baseline_model",),
            "human_review_required": False,
            "escalation": (),
        }
    )
    result = validate_ai_system_map(ai_map.model_copy(update={"tasks": (bad_task,)}))
    assert "SENSITIVE_TASK_CONTROL_REQUIRED" in {issue.code for issue in result.errors}


def test_regulated_risk_requires_review_blocking_or_escalation() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    bad_task = ai_map.tasks[0].model_copy(
        update={
            "category": "general",
            "risk_level": "regulated",
            "allowed_routes": ("baseline_model",),
            "human_review_required": False,
            "escalation": (),
        }
    )
    result = validate_ai_system_map(ai_map.model_copy(update={"tasks": (bad_task,)}))
    assert "SENSITIVE_TASK_CONTROL_REQUIRED" in {issue.code for issue in result.errors}


@pytest.mark.parametrize(
    ("suffix", "content"),
    [
        (
            ".yaml",
            """
schema_version: "1.0"
schema_version: "2.0"
system: {name: Duplicate Map, risk_profile: low}
""",
        ),
        (
            ".json",
            '{"schema_version":"1.0","schema_version":"2.0",'
            '"system":{"name":"Duplicate Map","risk_profile":"low"}}',
        ),
    ],
)
def test_ai_map_loader_rejects_duplicate_keys(tmp_path: Path, suffix: str, content: str) -> None:
    path = tmp_path / f"duplicate{suffix}"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(OntologyParseError, match="duplicate"):
        load_ai_system_map(path)


def test_ai_map_loader_bounds_list_item_lengths_without_echoing_input(
    tmp_path: Path,
) -> None:
    oversized = "sensitive-marker-" + "x" * 200
    path = tmp_path / "oversized.json"
    path.write_text(
        json.dumps(
            {
                "system": {"name": "Bounded Map", "risk_profile": "low"},
                "tasks": [
                    {
                        "name": "BoundedTask",
                        "risk_level": "low",
                        "allowed_routes": [oversized],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(OntologyParseError) as error:
        load_ai_system_map(path)
    assert "sensitive-marker" not in str(error.value)


def test_report_contains_required_sections_and_no_personal_markers() -> None:
    report = ai_system_map_report(load_ai_system_map(EXAMPLE))
    for section in (
        "Executive Summary",
        "System",
        "Business Entities",
        "AI Tasks",
        "Risk Summary",
        "Model Route Summary",
        "Human Review and Escalation",
        "Audit Expectations",
        "Cost and Outcome Measurement Expectations",
        "Linux of AI Integration Map",
        "Warnings",
        "Limitations",
        "Reproducibility",
    ):
        assert f"## {section}" in report
    assert report.startswith("# AI System Map Report")
    assert "sekacorn" not in report.casefold()
    assert "@" not in report
    assert "C:\\Users\\" not in report


def test_mermaid_contains_tasks_routes_entities_and_control_nodes() -> None:
    diagram = ai_system_map_mermaid(load_ai_system_map(EXAMPLE))
    assert "AI System: Customer Support AI" in diagram
    assert "Task: PasswordReset" in diagram
    assert "Entity: SupportTicket" in diagram
    assert "Route: candidate_model" in diagram
    assert "Escalation: legal_review" in diagram
    assert "Audit events" in diagram
    assert "Cost/outcome metrics" in diagram


def test_mermaid_keeps_duplicate_task_edges_on_their_own_nodes() -> None:
    ai_map = load_ai_system_map(EXAMPLE)
    first = ai_map.tasks[0].model_copy(
        update={"name": "DuplicateTask", "allowed_routes": ("candidate_model",)}
    )
    second = ai_map.tasks[1].model_copy(
        update={"name": "DuplicateTask", "allowed_routes": ("baseline_model",)}
    )
    diagram = ai_system_map_mermaid(ai_map.model_copy(update={"tasks": (first, second)}))
    assert "task_0001 -->|allowed| route_0001" in diagram
    assert "task_0002 -->|allowed| route_0002" in diagram


def test_ai_map_cli_help_validate_report_and_render(tmp_path: Path) -> None:
    help_result = runner.invoke(app, ["ai-map", "--help"])
    assert help_result.exit_code == 0
    assert "validate" in help_result.output
    assert "report" in help_result.output
    assert "render" in help_result.output

    report_path = tmp_path / "customer_support_ai_report.md"
    diagram_path = tmp_path / "customer_support_ai.mmd"
    commands = [
        ["ai-map", "validate", str(EXAMPLE)],
        [
            "ai-map",
            "report",
            str(EXAMPLE),
            "--format",
            "markdown",
            "--output",
            str(report_path),
        ],
        [
            "ai-map",
            "render",
            str(EXAMPLE),
            "--format",
            "mermaid",
            "--output",
            str(diagram_path),
        ],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
    report_text = report_path.read_text(encoding="utf-8")
    assert report_text.startswith("# AI System Map")
    assert "C:\\Users\\" not in report_text
    assert "- Source: customer\\_support\\_ai.yaml" in report_text
    assert diagram_path.read_text(encoding="utf-8").startswith("flowchart TD")


def test_ai_map_cli_strict_mode_fails_on_warning(tmp_path: Path) -> None:
    warning_map = tmp_path / "warning.yaml"
    warning_map.write_text(
        """
schema_version: "1.0"
system: {name: Warning Map, risk_profile: high}
entities: []
tasks:
  - name: HighRiskCandidate
    category: support
    risk_level: high
    allowed_routes: [candidate_model]
    audit_required: false
    cost_tracking_required: false
""",
        encoding="utf-8",
    )
    normal = runner.invoke(app, ["ai-map", "validate", str(warning_map)])
    strict = runner.invoke(app, ["ai-map", "validate", str(warning_map), "--strict"])
    assert normal.exit_code == 0
    assert strict.exit_code == 1
    assert "HIGH_RISK_CANDIDATE_ROUTE" in strict.output


def test_ai_map_cli_rejects_invalid_format() -> None:
    result = runner.invoke(app, ["ai-map", "render", str(EXAMPLE), "--format", "unsupported"])
    assert result.exit_code == 2
    assert "Unsupported render format" in result.stderr


def test_ai_map_cli_strips_terminal_control_characters(tmp_path: Path) -> None:
    path = tmp_path / "control.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "system": {"name": "Control Map", "risk_profile": "low"},
                "tasks": [
                    {
                        "name": "ControlTask",
                        "risk_level": "low",
                        "allowed_routes": ["\u001b[31muntrusted"],
                        "audit_required": False,
                        "cost_tracking_required": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["ai-map", "validate", str(path)])
    assert result.exit_code == 1
    assert "\u001b" not in result.output
    assert "INVALID_TASK_ROUTE" in result.output
