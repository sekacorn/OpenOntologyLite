"""Command-line interface for OpenOntologyLite."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from open_ontology_lite.ai_map import (
    AISystemMap,
    ai_system_map_mermaid,
    ai_system_map_report,
    load_ai_system_map,
    validate_ai_system_map,
)
from open_ontology_lite.contracts import generate_tool_contract
from open_ontology_lite.diffing import diff_ontologies, diff_text
from open_ontology_lite.errors import OpenOntologyLiteError
from open_ontology_lite.exporters import json_schema_text, markdown_docs, mermaid_text
from open_ontology_lite.exporters.escaping import plain
from open_ontology_lite.inspection import inspect_ontology
from open_ontology_lite.loading import load_ontology, load_raw
from open_ontology_lite.migrations import (
    build_migration_plan,
    migration_plan_json,
    migration_plan_markdown,
)
from open_ontology_lite.models import Ontology
from open_ontology_lite.normalization import canonical_json, ontology_digest
from open_ontology_lite.runtime import check_action_contract, validate_entity_instance
from open_ontology_lite.validation import find_cycles, validate_ontology
from open_ontology_lite.version import __version__

app = typer.Typer(no_args_is_help=True, add_completion=False)
entity_app = typer.Typer(no_args_is_help=True, add_completion=False, help="Validate entity data.")
action_app = typer.Typer(no_args_is_help=True, add_completion=False, help="Check action contracts.")
contract_app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Generate neutral handoff contracts."
)
ai_map_app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Validate and document portable AI workload maps.",
)
app.add_typer(ai_map_app, name="ai-map")
app.add_typer(entity_app, name="entity")
app.add_typer(action_app, name="action")
app.add_typer(contract_app, name="contract")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"openontology {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, help="Show version and exit."),
    ] = None,
) -> None:
    """Validate, inspect, normalize, export, and diff operational ontologies."""


def _fail(exc: Exception, *, debug: bool = False) -> NoReturn:
    if debug:
        raise exc
    typer.echo(plain(exc), err=True)
    raise typer.Exit(2)


def _write(text: str, output: Path | None) -> None:
    if output is None:
        typer.echo(text, nl=False)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _load(path: Path, debug: bool = False) -> Ontology:
    try:
        return load_ontology(path)
    except OpenOntologyLiteError as exc:
        _fail(exc, debug=debug)


def _load_ai_map(path: Path, debug: bool = False) -> AISystemMap:
    try:
        return load_ai_system_map(path)
    except OpenOntologyLiteError as exc:
        _fail(exc, debug=debug)


def _load_data(path: Path, debug: bool = False) -> dict[str, object]:
    try:
        return load_raw(path)
    except OpenOntologyLiteError as exc:
        _fail(exc, debug=debug)


def _runtime_text(result: object) -> str:
    issues = getattr(result, "issues", ())
    if not issues:
        return "Contract is satisfied.\n"
    return "".join(
        f"{issue.severity.upper()} {plain(issue.code)} {plain(issue.path)}: "
        f"{plain(issue.message)}\n"
        for issue in issues
    )


@entity_app.command("validate")
def entity_validate(
    ontology_file: Path,
    entity_type: str,
    instance: Path,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON result.")] = False,
    non_strict: Annotated[
        bool, typer.Option("--non-strict", help="Warn instead of error on unknown properties.")
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Validate one local JSON or YAML entity instance."""

    result = validate_entity_instance(
        _load(ontology_file, debug),
        entity_type=entity_type,
        value=_load_data(instance, debug),
        strict=not non_strict,
    )
    _write(
        json.dumps(result.to_dict(), sort_keys=True, indent=2) + "\n"
        if json_output
        else _runtime_text(result),
        None,
    )
    if not result.valid:
        raise typer.Exit(1)


@action_app.command("check")
def action_check(
    ontology_file: Path,
    action_name: str,
    inputs: Path,
    permissions: Annotated[
        list[str] | None,
        typer.Option("--permission", "-p", help="Permission held by the proposed actor."),
    ] = None,
    context: Annotated[
        Path | None, typer.Option("--context", help="Local JSON or YAML context object.")
    ] = None,
    output_value: Annotated[
        Path | None, typer.Option("--output-value", help="Local JSON or YAML output object.")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON result.")] = False,
    non_strict: Annotated[
        bool, typer.Option("--non-strict", help="Warn instead of error on unknown inputs.")
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Check a proposed invocation without making an authorization decision."""

    result = check_action_contract(
        _load(ontology_file, debug),
        action=action_name,
        inputs=_load_data(inputs, debug),
        actor_permissions=permissions or (),
        context=_load_data(context, debug) if context else None,
        output=_load_data(output_value, debug) if output_value else None,
        strict=not non_strict,
    )
    _write(
        json.dumps(result.to_dict(), sort_keys=True, indent=2) + "\n"
        if json_output
        else _runtime_text(result),
        None,
    )
    if result.status == "unsatisfied":
        raise typer.Exit(1)
    if result.status == "indeterminate":
        raise typer.Exit(3)


@contract_app.command("tool")
def contract_tool(
    ontology_file: Path,
    action_name: str,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Generate a neutral Forge-compatible tool description."""

    try:
        contract = generate_tool_contract(_load(ontology_file, debug), action_name)
    except KeyError as exc:
        _fail(exc, debug=debug)
    _write(json.dumps(contract.to_dict(), sort_keys=True, indent=2) + "\n", output)


def _require_valid(ontology: Ontology) -> None:
    report = validate_ontology(ontology)
    if report.errors:
        first = report.errors[0]
        typer.echo(
            "Cannot export invalid ontology: "
            f"{plain(first.code)} {plain(first.path)}: {plain(first.message)}",
            err=True,
        )
        raise typer.Exit(1)


def _require_valid_ai_map(ai_map: AISystemMap, *, fail_on_warning: bool = False) -> None:
    report = validate_ai_system_map(ai_map)
    if report.errors or (fail_on_warning and report.warnings):
        for issue in report.issues:
            typer.echo(
                f"{issue.severity.upper()} {plain(issue.code)} "
                f"{plain(issue.path)}: {plain(issue.message)}",
                err=True,
            )
        raise typer.Exit(1)


@ai_map_app.command("validate")
def ai_map_validate(
    file: Path,
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit a JSON validation result.")
    ] = False,
    fail_on_warning: Annotated[
        bool,
        typer.Option(
            "--strict",
            "--fail-on-warning",
            help="Exit nonzero when validation produces warnings.",
        ),
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Validate an AI System Map."""

    result = validate_ai_system_map(_load_ai_map(file, debug))
    if json_output:
        typer.echo(json.dumps(result.to_dict(), sort_keys=True, indent=2))
    elif result.valid and not result.warnings:
        typer.echo("AI System Map is valid.")
    else:
        for issue in result.issues:
            typer.echo(
                f"{issue.severity.upper()} {plain(issue.code)} "
                f"{plain(issue.path)}: {plain(issue.message)}"
            )
        if result.valid:
            typer.echo(f"AI System Map is valid with {len(result.warnings)} warning(s).")
    if result.errors or (fail_on_warning and result.warnings):
        raise typer.Exit(1)


@ai_map_app.command("report")
def ai_map_report_cmd(
    file: Path,
    format_name: Annotated[
        str, typer.Option("--format", help="Report format (markdown).")
    ] = "markdown",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    fail_on_warning: Annotated[
        bool,
        typer.Option(
            "--strict",
            "--fail-on-warning",
            help="Exit nonzero when validation produces warnings.",
        ),
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Generate a deterministic AI System Map report."""

    if format_name.casefold() not in {"markdown", "md"}:
        typer.echo("Unsupported report format. Use markdown.", err=True)
        raise typer.Exit(2)
    ai_map = _load_ai_map(file, debug)
    _require_valid_ai_map(ai_map, fail_on_warning=fail_on_warning)
    result = validate_ai_system_map(ai_map)
    _write(ai_system_map_report(ai_map, validation=result, source=file.name), output)


@ai_map_app.command("render")
def ai_map_render(
    file: Path,
    format_name: Annotated[
        str, typer.Option("--format", help="Render format (mermaid).")
    ] = "mermaid",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    fail_on_warning: Annotated[
        bool,
        typer.Option(
            "--strict",
            "--fail-on-warning",
            help="Exit nonzero when validation produces warnings.",
        ),
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Render an AI System Map."""

    if format_name.casefold() not in {"mermaid", "mmd"}:
        typer.echo("Unsupported render format. Use mermaid.", err=True)
        raise typer.Exit(2)
    ai_map = _load_ai_map(file, debug)
    _require_valid_ai_map(ai_map, fail_on_warning=fail_on_warning)
    _write(ai_system_map_mermaid(ai_map), output)


@app.command()
def version() -> None:
    """Show the OpenOntologyLite version."""

    typer.echo(__version__)


@app.command()
def validate(
    file: Path,
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit JSON validation report.")
    ] = False,
    non_strict_permissions: Annotated[
        bool, typer.Option("--non-strict-permissions", help="Warn on undeclared permissions.")
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Validate an ontology file."""

    ontology = _load(file, debug)
    report = validate_ontology(ontology, strict_permissions=not non_strict_permissions)
    if json_output:
        typer.echo(json.dumps(report.to_dict(), sort_keys=True, indent=2))
    elif report.ok:
        typer.echo("Ontology is valid.")
        if report.warnings:
            typer.echo(f"Warnings: {len(report.warnings)}")
    else:
        for issue in report.issues:
            typer.echo(
                f"{issue.severity.upper()} {plain(issue.code)} "
                f"{plain(issue.path)}: {plain(issue.message)}"
            )
    if report.errors:
        raise typer.Exit(1)


@app.command()
def inspect(
    file: Path,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON summary.")] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Inspect an ontology."""

    summary = inspect_ontology(_load(file, debug))
    if json_output:
        typer.echo(json.dumps(summary.model_dump(), sort_keys=True, indent=2))
    else:
        for key, value in summary.model_dump().items():
            typer.echo(f"{plain(key)}: {plain(value)}")


@app.command()
def normalize(
    file: Path,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Emit canonical normalized JSON."""

    _write(canonical_json(_load(file, debug)), output)


@app.command()
def digest(
    file: Path,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Print the canonical SHA-256 digest."""

    typer.echo(ontology_digest(_load(file, debug)))


@app.command()
def cycles(
    file: Path,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON cycles.")] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Analyze entity relationship and reference cycles."""

    found = find_cycles(_load(file, debug))
    if json_output:
        typer.echo(json.dumps([cycle.model_dump() for cycle in found], sort_keys=True, indent=2))
    elif not found:
        typer.echo("No cycles detected.")
    else:
        for cycle in found:
            typer.echo(
                f"{plain(cycle.classification)}: {' -> '.join(plain(part) for part in cycle.path)}"
            )


@app.command("export-json-schema")
def export_json_schema(
    file: Path,
    entity: Annotated[
        str | None, typer.Option("--entity", help="Export one entity schema.")
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Export deterministic JSON Schema."""

    ontology = _load(file, debug)
    _require_valid(ontology)
    if entity and entity not in ontology.entities:
        typer.echo(f"Unknown entity: {plain(entity)}", err=True)
        raise typer.Exit(2)
    _write(json_schema_text(ontology, entity), output)


@app.command("export-mermaid")
def export_mermaid(
    file: Path,
    detailed: Annotated[bool, typer.Option("--detailed", help="Include properties.")] = False,
    compact: Annotated[bool, typer.Option("--compact", help="Omit details.")] = False,
    actions: Annotated[bool, typer.Option("--actions", help="Include action summaries.")] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Export Mermaid source text."""

    ontology = _load(file, debug)
    _require_valid(ontology)
    _write(
        mermaid_text(ontology, detailed=detailed and not compact, include_actions=actions),
        output,
    )


@app.command("docs")
def docs_cmd(
    file: Path,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    include_timestamp: Annotated[
        bool, typer.Option("--include-timestamp", help="Include generation timestamp.")
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Generate deterministic Markdown documentation."""

    ontology = _load(file, debug)
    _require_valid(ontology)
    _write(
        markdown_docs(
            ontology, validation=validate_ontology(ontology), include_timestamp=include_timestamp
        ),
        output,
    )


@app.command()
def diff(
    old_file: Path,
    new_file: Path,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON diff.")] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Diff two ontology versions. Exit 1 when breaking changes are detected."""

    old = _load(old_file, debug)
    new = _load(new_file, debug)
    result = diff_ontologies(old, new)
    text = (
        json.dumps(result.to_dict(), sort_keys=True, indent=2) + "\n"
        if json_output
        else diff_text(result)
    )
    _write(text, output)
    if result.breaking_count:
        raise typer.Exit(1)


@app.command("migration-plan")
def migration_plan(
    old_file: Path,
    new_file: Path,
    format_name: Annotated[
        str, typer.Option("--format", help="Output format: json or markdown.")
    ] = "json",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write output to a file.")
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show stack traces for maintainers.")
    ] = False,
) -> None:
    """Generate deterministic, non-mutating migration guidance."""

    plan = build_migration_plan(_load(old_file, debug), _load(new_file, debug))
    normalized_format = format_name.casefold()
    if normalized_format == "json":
        text = migration_plan_json(plan)
    elif normalized_format in {"markdown", "md"}:
        text = migration_plan_markdown(plan)
    else:
        typer.echo("Unsupported migration-plan format. Use json or markdown.", err=True)
        raise typer.Exit(2)
    _write(text, output)


def run() -> None:
    """Run the CLI app."""

    try:
        app()
    except BrokenPipeError:
        sys.exit(1)
