"""Local module security and new CLI command tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from open_ontology_lite.ai_map import load_ai_system_map, validate_ai_system_map
from open_ontology_lite.cli import app
from open_ontology_lite.errors import ModuleResolutionError, UnsafeInputError
from open_ontology_lite.loading import load_ontology
from open_ontology_lite.modules import resolve_local_modules

ROOT = Path(__file__).parents[1]
runner = CliRunner()

MODULE = """schema_version: "1.0"
ontology:
  id: shared
  name: Shared module
  version: "1.2.0"
  namespace: example.shared
entities:
  Item:
    properties:
      item_id: {type: string, required: true}
permissions:
  shared.read: {}
actions:
  - name: read_item
    subject: Item
    inputs:
      item: {type: reference, target: Item}
    permissions: [shared.read]
"""


def _root(import_block: str) -> str:
    return f"""schema_version: "1.0"
ontology:
  id: root
  name: Root ontology
  version: "1.0.0"
  namespace: example.root
imports:
{import_block}
entities:
  Root:
    properties:
      root_id: {{type: string, required: true}}
"""


def test_local_module_resolution_merge_and_provenance(tmp_path: Path) -> None:
    module = tmp_path / "shared.yaml"
    root = tmp_path / "root.yaml"
    module.write_text(MODULE, encoding="utf-8")
    root.write_text(
        _root(
            """  - path: shared.yaml
    namespace: example.shared
    version: ">=1.0,<2.0"
"""
        ),
        encoding="utf-8",
    )
    result = resolve_local_modules(root)
    assert "example__shared__Item" in result.ontology.entities
    assert "example__shared__read_item" in {action.name for action in result.ontology.actions}
    assert result.provenance["entities.example__shared__Item"] == "example.shared"
    assert [module.namespace for module in result.modules] == ["example.root", "example.shared"]
    assert result.modules[1].path == "shared.yaml"


def test_module_digest_version_namespace_and_remote_fail_closed(tmp_path: Path) -> None:
    (tmp_path / "shared.yaml").write_text(MODULE, encoding="utf-8")
    cases = [
        """  - path: shared.yaml
    version: ">=2.0"
""",
        """  - path: shared.yaml
    namespace: example.wrong
""",
        """  - path: shared.yaml
    digest: deadbeef
""",
        """  - path: https://example.invalid/module.yaml
""",
    ]
    for index, declaration in enumerate(cases):
        root = tmp_path / f"root-{index}.yaml"
        root.write_text(_root(declaration), encoding="utf-8")
        with pytest.raises(ModuleResolutionError):
            resolve_local_modules(root)


def test_module_cycles_and_boundary_traversal_are_rejected(tmp_path: Path) -> None:
    graph = tmp_path / "graph"
    graph.mkdir()
    root = graph / "root.yaml"
    child = graph / "child.yaml"
    root.write_text(_root("  - path: child.yaml\n"), encoding="utf-8")
    child.write_text(
        MODULE.replace(
            "entities:\n",
            "imports:\n  - path: root.yaml\nentities:\n",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ModuleResolutionError, match="cycle"):
        resolve_local_modules(root)

    outside = tmp_path / "outside.yaml"
    outside.write_text(MODULE, encoding="utf-8")
    traversal = graph / "traversal.yaml"
    traversal.write_text(_root("  - path: ../outside.yaml\n"), encoding="utf-8")
    with pytest.raises(ModuleResolutionError, match="boundary"):
        resolve_local_modules(traversal)


def test_module_definition_conflicts_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "shared.yaml").write_text(MODULE, encoding="utf-8")
    root = tmp_path / "root.yaml"
    content = _root("  - path: shared.yaml\n").replace(
        "entities:\n",
        "entities:\n  example__shared__Item: {properties: {}}\n",
    )
    root.write_text(content, encoding="utf-8")
    with pytest.raises(ModuleResolutionError, match="Conflicting entity"):
        resolve_local_modules(root)


def test_loader_rejects_symbolic_links_when_supported(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    link = tmp_path / "link.yaml"
    target.write_text(MODULE, encoding="utf-8")
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("Symbolic link creation is unavailable.")
    with pytest.raises(UnsafeInputError):
        load_ontology(link)


def test_runtime_contract_and_migration_cli_commands(tmp_path: Path) -> None:
    ontology = ROOT / "examples" / "customer_support.yaml"
    instance = tmp_path / "customer.json"
    inputs = tmp_path / "inputs.json"
    instance.write_text('{"customer_id": "C-1"}', encoding="utf-8")
    inputs.write_text(
        '{"customer_id": "C-1", "description": "Need assistance"}',
        encoding="utf-8",
    )

    entity = runner.invoke(
        app,
        ["entity", "validate", str(ontology), "Customer", str(instance), "--json"],
    )
    assert entity.exit_code == 0, entity.output
    assert json.loads(entity.output)["defaults_required"] is True

    action = runner.invoke(
        app,
        [
            "action",
            "check",
            str(ontology),
            "create_ticket",
            str(inputs),
            "--permission",
            "support.ticket.create",
            "--json",
        ],
    )
    assert action.exit_code == 0, action.output
    assert json.loads(action.output)["status"] == "satisfied"

    tool = runner.invoke(app, ["contract", "tool", str(ontology), "create_ticket"])
    assert tool.exit_code == 0, tool.output
    assert json.loads(tool.output)["contract_type"] == "tool"

    migration = runner.invoke(
        app,
        [
            "migration-plan",
            str(ROOT / "tests" / "fixtures" / "diff" / "customer-support-v1.yaml"),
            str(ROOT / "tests" / "fixtures" / "diff" / "customer-support-v2.yaml"),
            "--format",
            "markdown",
        ],
    )
    assert migration.exit_code == 0, migration.output
    assert migration.output.startswith("# Ontology migration plan")


def test_runtime_cli_failure_exit_codes(tmp_path: Path) -> None:
    ontology = ROOT / "examples" / "customer_support.yaml"
    bad = tmp_path / "bad.json"
    bad.write_text('{"unknown": true}', encoding="utf-8")
    entity = runner.invoke(
        app,
        ["entity", "validate", str(ontology), "Customer", str(bad)],
    )
    assert entity.exit_code == 1
    assert "REQUIRED_PROPERTY_MISSING" in entity.output

    action = runner.invoke(
        app,
        ["action", "check", str(ontology), "missing", str(bad), "--json"],
    )
    assert action.exit_code == 1
    assert json.loads(action.output)["status"] == "unsatisfied"

    invalid_format = runner.invoke(
        app,
        [
            "migration-plan",
            str(ontology),
            str(ontology),
            "--format",
            "xml",
        ],
    )
    assert invalid_format.exit_code == 2


def test_expanded_ai_map_ontology_reference_validation() -> None:
    ontology = load_ontology(ROOT / "examples" / "customer_support.yaml")
    ai_map = load_ai_system_map(ROOT / "examples" / "ai_system_map" / "customer_support_ai.yaml")
    task = ai_map.tasks[0].model_copy(
        update={
            "ontology_entities": ("MissingEntity",),
            "ontology_actions": ("missing_action",),
            "ontology_permissions": ("missing.permission",),
            "escalation_required": True,
            "escalation": (),
        }
    )
    changed = ai_map.model_copy(update={"tasks": (task, *ai_map.tasks[1:])})
    result = validate_ai_system_map(changed, ontology)
    codes = {issue.code for issue in result.issues}
    assert {
        "UNKNOWN_ONTOLOGY_ENTITY",
        "UNKNOWN_ONTOLOGY_ACTION",
        "UNKNOWN_ONTOLOGY_PERMISSION",
        "ESCALATION_ROUTE_REQUIRED",
    } <= codes
