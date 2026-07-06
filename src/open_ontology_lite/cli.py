"""Command-line interface for OpenOntologyLite."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from open_ontology_lite.diffing import diff_ontologies, diff_text
from open_ontology_lite.errors import OpenOntologyLiteError
from open_ontology_lite.exporters import json_schema_text, markdown_docs, mermaid_text
from open_ontology_lite.inspection import inspect_ontology
from open_ontology_lite.loading import load_ontology
from open_ontology_lite.models import Ontology
from open_ontology_lite.normalization import canonical_json, ontology_digest
from open_ontology_lite.validation import find_cycles, validate_ontology
from open_ontology_lite.version import __version__

app = typer.Typer(no_args_is_help=True, add_completion=False)


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
    typer.echo(str(exc), err=True)
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


def _require_valid(ontology: Ontology) -> None:
    report = validate_ontology(ontology)
    if report.errors:
        first = report.errors[0]
        typer.echo(
            f"Cannot export invalid ontology: {first.code} {first.path}: {first.message}",
            err=True,
        )
        raise typer.Exit(1)


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
            typer.echo(f"{issue.severity.upper()} {issue.code} {issue.path}: {issue.message}")
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
            typer.echo(f"{key}: {value}")


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
            typer.echo(f"{cycle.classification}: {' -> '.join(cycle.path)}")


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
        typer.echo(f"Unknown entity: {entity}", err=True)
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


def run() -> None:
    """Run the CLI app."""

    try:
        app()
    except BrokenPipeError:
        sys.exit(1)
