"""Safe ontology loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from open_ontology_lite.errors import OntologyLoadError, OntologyParseError, UnsafeInputError
from open_ontology_lite.models import Ontology

MAX_FILE_SIZE = 2_000_000
MAX_NESTING_DEPTH = 40
MAX_INPUT_NODES = 100_000


def _depth(value: object, current: int = 0) -> int:
    max_depth = current
    node_count = 0
    stack = [(value, current)]
    while stack:
        item, depth = stack.pop()
        node_count += 1
        if node_count > MAX_INPUT_NODES:
            raise UnsafeInputError(f"Ontology input exceeds {MAX_INPUT_NODES} parsed nodes.")
        max_depth = max(max_depth, depth)
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
    return max_depth


def _ensure_safe_path(path: Path) -> None:
    try:
        stat = path.stat()
    except OSError as exc:
        raise OntologyLoadError(f"Cannot inspect ontology path: {path}") from exc
    if path.is_dir():
        raise OntologyLoadError(f"Ontology path is a directory: {path}")
    if stat.st_size > MAX_FILE_SIZE:
        raise UnsafeInputError(f"Ontology file exceeds {MAX_FILE_SIZE} bytes: {path}")


def load_raw(path: str | Path) -> dict[str, Any]:
    """Load raw YAML or JSON using safe parsers."""

    source = Path(path)
    if not source.exists():
        raise OntologyLoadError(f"Ontology file not found: {source}")
    _ensure_safe_path(source)
    suffix = source.suffix.lower()
    try:
        text = source.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise OntologyParseError(f"Ontology file is not valid UTF-8: {source}") from exc
    except OSError as exc:
        raise OntologyLoadError(f"Cannot read ontology file: {source}") from exc
    if not text.strip():
        raise OntologyParseError("Ontology file is empty.")
    try:
        if suffix in {".yaml", ".yml"}:
            loaded = yaml.safe_load(text)
        elif suffix == ".json":
            loaded = json.loads(text)
        else:
            raise OntologyLoadError(f"Unsupported ontology file extension: {suffix}")
    except yaml.YAMLError as exc:
        raise OntologyParseError(f"Malformed YAML: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise OntologyParseError(f"Malformed JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise OntologyParseError("Ontology root must be an object.")
    if _depth(loaded) > MAX_NESTING_DEPTH:
        raise UnsafeInputError(f"Ontology nesting exceeds {MAX_NESTING_DEPTH} levels.")
    return loaded


def load_ontology(path: str | Path) -> Ontology:
    """Load a YAML or JSON ontology file into an immutable model."""

    raw = load_raw(path)
    try:
        return Ontology.model_validate(raw)
    except ValidationError as exc:
        raise OntologyParseError(str(exc)) from exc
