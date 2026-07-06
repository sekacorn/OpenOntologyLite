from pathlib import Path

import pytest
from typer.testing import CliRunner

from open_ontology_lite import (
    diff_ontologies,
    inspect_ontology,
    load_ontology,
    normalize_ontology,
    ontology_digest,
    validate_ontology,
)
from open_ontology_lite.cli import app
from open_ontology_lite.errors import OntologyLoadError, OntologyParseError, UnsafeInputError
from open_ontology_lite.exporters import json_schema_text, markdown_docs, mermaid_text
from open_ontology_lite.loading.json_loader import load_raw as load_json_raw
from open_ontology_lite.loading.yaml_loader import load_raw as load_yaml_raw
from open_ontology_lite.normalization import canonical_json
from open_ontology_lite.validation import find_cycles
from open_ontology_lite.validation.structural import validate_structure

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
FIXTURES = ROOT / "tests" / "fixtures"
runner = CliRunner()


def test_valid_examples_load_and_validate() -> None:
    for path in EXAMPLES.glob("*.yaml"):
        ontology = load_ontology(path)
        report = validate_ontology(ontology)
        assert report.ok, path
        assert inspect_ontology(ontology).entity_count >= 5


@pytest.mark.parametrize(
    ("fixture", "code"),
    [
        ("unknown_relationship_target.yaml", "RELATIONSHIP_TARGET_NOT_FOUND"),
        ("duplicate_action.yaml", "ACTION_DUPLICATE"),
        ("undeclared_permission.yaml", "PERMISSION_UNDECLARED"),
        ("invalid_enum_default.yaml", "PROPERTY_DEFAULT_NOT_IN_ENUM"),
        ("incompatible_numeric_constraint.yaml", "PROPERTY_NUMERIC_LIMIT_INVALID_TYPE"),
        ("unsupported_schema.yaml", "SCHEMA_VERSION_UNSUPPORTED"),
        ("empty_precondition.yaml", "PRECONDITION_EMPTY"),
        ("invalid_identifier.yaml", "IDENTIFIER_INVALID"),
    ],
)
def test_invalid_fixtures_report_stable_codes(fixture: str, code: str) -> None:
    ontology = load_ontology(FIXTURES / "invalid" / fixture)
    report = validate_ontology(ontology)
    assert code in {issue.code for issue in report.issues}
    assert not report.ok


def test_malformed_yaml_rejected() -> None:
    with pytest.raises(OntologyParseError):
        load_ontology(FIXTURES / "invalid" / "malformed.yaml")


def test_non_strict_permission_warning() -> None:
    ontology = load_ontology(FIXTURES / "invalid" / "undeclared_permission.yaml")
    report = validate_ontology(ontology, strict_permissions=False)
    assert not report.errors
    assert report.warnings[0].code == "PERMISSION_UNDECLARED"


def test_canonical_digest_stable_for_reordered_yaml(tmp_path: Path) -> None:
    a = EXAMPLES / "customer_support.yaml"
    b = tmp_path / "customer_support_reordered.yaml"
    b.write_text(
        """
entities:
  Customer:
    properties:
      created_at: {type: datetime}
      account_status:
        default: active
        enum: [active, suspended, closed]
        required: true
        type: string
      customer_id: {required: true, type: string}
    description: A person or organization receiving services.
  Agent:
    properties:
      display_name: {min_length: 1, required: true, type: string}
      agent_id: {required: true, type: uuid}
    description: A staff member or agent handling customer work.
  Invoice:
    description: A bill issued to a customer.
    properties:
      customer: {target: Customer, type: reference}
      status: {enum: [draft, issued, paid, void], required: true, type: string}
      amount: {minimum: 0, required: true, type: decimal}
      invoice_id: {required: true, type: string}
  Refund:
    properties:
      invoice: {target: Invoice, type: reference}
      amount: {minimum: 0, required: true, type: decimal}
      refund_id: {required: true, type: string}
    description: A refund issued for an invoice.
  SupportTicket:
    properties:
      customer: {target: Customer, type: reference}
      status: {default: open, enum: [open, assigned, closed], required: true, type: string}
      ticket_id: {required: true, type: string}
    description: A customer support request.
actions:
  - subject: SupportTicket
    name: assign_ticket
    inputs:
      agent_id: {required: true, type: uuid}
    permissions: [support.ticket.assign]
  - subject: SupportTicket
    name: create_ticket
    description: Creates a support ticket.
    inputs:
      description: {min_length: 1, required: true, type: string}
      customer_id: {required: true, type: string}
    permissions: [support.ticket.create]
  - subject: SupportTicket
    name: close_ticket
    permissions: [support.ticket.close]
    preconditions: ['ticket.status != "closed"']
  - subject: Invoice
    name: issue_refund
    description: Issues a refund for a paid invoice.
    inputs:
      amount: {minimum: 0, required: true, type: decimal}
      reason: {required: true, type: string}
    output: {target: Refund, type: reference}
    permissions: [billing.refund]
    preconditions: ['invoice.status == "paid"', 'amount <= invoice.amount']
permissions:
  billing.refund: {description: Allows issuing refunds., risk: high}
  support.ticket.assign: {description: Allows assigning tickets., risk: medium}
  support.ticket.close: {description: Allows closing tickets., risk: medium}
  support.ticket.create: {description: Allows ticket creation., risk: low}
relationships:
  - {name: customer_opens_tickets, from: Customer, to: SupportTicket, cardinality: one_to_many}
  - {name: agent_handles_ticket, from: Agent, to: SupportTicket, cardinality: one_to_many}
  - {name: customer_has_invoices, from: Customer, to: Invoice, cardinality: one_to_many}
ontology:
  tags: [support, billing]
  description: Operational concepts for customer service workflows.
  namespace: example.customer_service
  version: "1.0.0"
  name: Customer Service Ontology
  id: customer-service
schema_version: "1.0"
""",
        encoding="utf-8",
    )
    assert ontology_digest(load_ontology(a)) == ontology_digest(load_ontology(b))


def test_exports_are_deterministic() -> None:
    ontology = load_ontology(EXAMPLES / "customer_support.yaml")
    outputs = [
        canonical_json(ontology),
        json_schema_text(ontology),
        mermaid_text(ontology, detailed=True, include_actions=True),
        markdown_docs(ontology, validation=validate_ontology(ontology)),
    ]
    assert outputs == [
        canonical_json(ontology),
        json_schema_text(ontology),
        mermaid_text(ontology, detailed=True, include_actions=True),
        markdown_docs(ontology, validation=validate_ontology(ontology)),
    ]
    assert '"$defs"' in outputs[1]
    assert "classDiagram" in outputs[2]
    assert "Validation Summary" in outputs[3]


def test_cycles_detect_reference_cycle(tmp_path: Path) -> None:
    path = tmp_path / "cycle.yaml"
    path.write_text(
        """
schema_version: "1.0"
ontology: {id: cyclic, name: Cyclic, version: "1", namespace: example.cyclic}
entities:
  A: {properties: {b: {type: reference, target: B}}}
  B: {properties: {a: {type: reference, target: A}}}
""",
        encoding="utf-8",
    )
    cycles = find_cycles(load_ontology(path))
    assert cycles
    assert cycles[0].path[0] == "A"


def test_diff_classifies_breaking_changes() -> None:
    old = load_ontology(FIXTURES / "diff" / "customer-support-v1.yaml")
    new = load_ontology(FIXTURES / "diff" / "customer-support-v2.yaml")
    result = diff_ontologies(old, new)
    codes = {change.code for change in result.changes}
    assert {
        "ENUM_VALUE_REMOVED",
        "REQUIRED_PROPERTY_ADDED",
        "RELATIONSHIP_REMOVED",
        "ACTION_REMOVED",
        "PERMISSION_REMOVED",
    } <= codes
    assert result.breaking_count >= 5


def test_diff_uses_aliases_for_renames(tmp_path: Path) -> None:
    old_path = tmp_path / "old.yaml"
    new_path = tmp_path / "new.yaml"
    old_path.write_text(
        """
schema_version: "1.0"
ontology: {id: rename, name: Rename, version: "1", namespace: example.rename}
entities:
  Customer:
    properties:
      customer_id: {type: string, required: true}
relationships:
  - {name: customer_links_customer, from: Customer, to: Customer, cardinality: one_to_one}
actions:
  - {name: update_customer, subject: Customer}
""",
        encoding="utf-8",
    )
    new_path.write_text(
        """
schema_version: "1.0"
ontology: {id: rename, name: Rename, version: "2", namespace: example.rename}
entities:
  Client:
    aliases: [Customer]
    properties:
      client_id: {type: string, required: true, aliases: [customer_id]}
relationships:
  - name: client_links_client
    aliases: [customer_links_customer]
    from: Client
    to: Client
    cardinality: one_to_one
actions:
  - name: update_client
    aliases: [update_customer]
    subject: Client
""",
        encoding="utf-8",
    )
    result = diff_ontologies(load_ontology(old_path), load_ontology(new_path))
    codes = {change.code for change in result.changes}
    assert {"ENTITY_RENAMED", "RELATIONSHIP_RENAMED", "ACTION_RENAMED"} <= codes
    assert "ENTITY_REMOVED" not in codes
    assert "ACTION_REMOVED" not in codes


def test_alias_validation() -> None:
    ontology = load_ontology(EXAMPLES / "customer_support.yaml").model_copy(
        update={
            "entities": {
                **load_ontology(EXAMPLES / "customer_support.yaml").entities,
                "Bad": load_ontology(EXAMPLES / "customer_support.yaml")
                .entities["Customer"]
                .model_copy(update={"aliases": ("123Bad", "123Bad")}),
            }
        }
    )
    codes = {issue.code for issue in validate_ontology(ontology).issues}
    assert {"ALIAS_INVALID", "ALIAS_DUPLICATE"} <= codes


def test_public_api_normalize_returns_dict() -> None:
    ontology = load_ontology(EXAMPLES / "customer_support.yaml")
    normalized = normalize_ontology(ontology)
    assert normalized["ontology"]["id"] == "customer-service"
    assert ontology_digest(ontology)


def test_cli_acceptance_commands(tmp_path: Path) -> None:
    example = str(EXAMPLES / "customer_support.yaml")
    for command in [
        ["validate", example],
        ["inspect", example],
        ["normalize", example],
        ["digest", example],
        ["cycles", example],
        ["export-json-schema", example, "--output", str(tmp_path / "schema.json")],
        ["export-mermaid", example, "--output", str(tmp_path / "diagram.mmd")],
        ["docs", example, "--output", str(tmp_path / "docs.md")],
    ]:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
    diff_result = runner.invoke(
        app,
        [
            "diff",
            str(FIXTURES / "diff" / "customer-support-v1.yaml"),
            str(FIXTURES / "diff" / "customer-support-v2.yaml"),
        ],
    )
    assert diff_result.exit_code == 1
    assert "Breaking:" in diff_result.output


def test_cli_json_modes_and_version() -> None:
    example = str(EXAMPLES / "customer_support.yaml")
    assert runner.invoke(app, ["--version"]).exit_code == 0
    assert runner.invoke(app, ["version"]).output.strip() == "0.1.0a2"
    assert '"ok": true' in runner.invoke(app, ["validate", example, "--json"]).output
    assert "canonical_digest" in runner.invoke(app, ["inspect", example, "--json"]).output
    assert runner.invoke(app, ["cycles", example, "--json"]).exit_code == 0


def test_json_loading_and_compatibility_modules(tmp_path: Path) -> None:
    path = tmp_path / "ontology.json"
    path.write_text(
        """{
          "schema_version": "1.0",
          "ontology": {
            "id": "json-test",
            "name": "JSON Test",
            "version": "1",
            "namespace": "example.json"
          },
          "entities": {"Thing": {"properties": {"id": {"type": "string", "required": true}}}}
        }""",
        encoding="utf-8",
    )
    assert load_json_raw(path)["schema_version"] == "1.0"
    assert load_yaml_raw(EXAMPLES / "customer_support.yaml")["schema_version"] == "1.0"
    assert validate_structure(load_ontology(path)).ok


def test_loader_rejects_empty_unsupported_directory_and_bad_json(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{", encoding="utf-8")
    unsupported = tmp_path / "ontology.txt"
    unsupported.write_text("schema_version: '1.0'", encoding="utf-8")
    with pytest.raises(OntologyParseError):
        load_ontology(empty)
    with pytest.raises(OntologyParseError):
        load_ontology(bad_json)
    with pytest.raises(OntologyLoadError):
        load_ontology(unsupported)
    with pytest.raises(OntologyLoadError):
        load_ontology(tmp_path)


def test_json_schema_property_type_branches(tmp_path: Path) -> None:
    path = tmp_path / "types.yaml"
    path.write_text(
        """
schema_version: "1.0"
ontology: {id: types, name: Types, version: "1", namespace: example.types}
entities:
  Other:
    properties:
      id: {type: string, required: true}
  Thing:
    description: Type coverage.
    properties:
      count: {type: integer, minimum: 1, maximum: 5}
      ratio: {type: number}
      price: {type: decimal}
      flag: {type: boolean}
      due: {type: date}
      at: {type: datetime}
      uid: {type: uuid}
      attrs: {type: object}
      tags: {type: array, items: string, min_length: 1, max_length: 3}
      other: {type: reference, target: Other, nullable: true}
""",
        encoding="utf-8",
    )
    ontology = load_ontology(path)
    report = validate_ontology(ontology)
    assert report.ok
    schema = json_schema_text(ontology, "Thing")
    assert '"format": "date-time"' in schema
    assert '"type": "array"' in schema
    assert '"$ref": "#/$defs/Other"' in schema
    assert '"anyOf"' in schema


def test_more_validation_limit_and_text_branches(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
schema_version: "1.0"
ontology: {id: bad, name: Bad, version: "1", namespace: bad namespace}
entities:
  Thing:
    properties:
      ref: {type: reference}
      arr: {type: array}
      text: {type: string, min_length: 4, max_length: 2}
      amount: {type: decimal, minimum: 10, maximum: 1}
      obj: {type: object, enum: ["wrong"]}
actions:
  - name: do_it
    subject: Missing
    inputs:
      bad-input: {type: string}
    output: {type: reference, target: Missing}
    permissions: [""]
    preconditions: ["valid text"]
permissions:
  Bad.Permission: {risk: low}
""",
        encoding="utf-8",
    )
    codes = {issue.code for issue in validate_ontology(load_ontology(path)).issues}
    assert {
        "NAMESPACE_INVALID",
        "PROPERTY_REFERENCE_TARGET_REQUIRED",
        "PROPERTY_ARRAY_ITEMS_REQUIRED",
        "PROPERTY_LENGTH_RANGE_INVALID",
        "PROPERTY_LIMIT_RANGE_INVALID",
        "PROPERTY_ENUM_TYPE_INVALID",
        "ACTION_SUBJECT_NOT_FOUND",
        "PERMISSION_EMPTY",
        "PERMISSION_NAME_INVALID",
    } <= codes


def test_cli_error_paths_and_run_helper() -> None:
    result = runner.invoke(
        app, ["export-json-schema", str(EXAMPLES / "customer_support.yaml"), "--entity", "Missing"]
    )
    assert result.exit_code == 2
    result = runner.invoke(
        app, ["validate", str(FIXTURES / "invalid" / "unknown_relationship_target.yaml")]
    )
    assert result.exit_code == 1


def test_cli_exports_reject_invalid_ontology(tmp_path: Path) -> None:
    invalid = str(FIXTURES / "invalid" / "unknown_relationship_target.yaml")
    commands = [
        ["export-json-schema", invalid, "--output", str(tmp_path / "schema.json")],
        ["export-mermaid", invalid, "--output", str(tmp_path / "diagram.mmd")],
        ["docs", invalid, "--output", str(tmp_path / "docs.md")],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 1
        assert "Cannot export invalid ontology" in result.stderr


def test_loader_rejects_excessive_parsed_nodes(tmp_path: Path) -> None:
    path = tmp_path / "too_many_nodes.json"
    path.write_text('{"nodes":[' + ",".join("0" for _ in range(100_001)) + "]}", encoding="utf-8")
    with pytest.raises(UnsafeInputError, match="parsed nodes"):
        load_json_raw(path)
