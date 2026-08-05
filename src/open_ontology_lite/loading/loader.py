"""Safe ontology loading."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, ScalarNode
from yaml.resolver import BaseResolver

from open_ontology_lite.errors import OntologyLoadError, OntologyParseError, UnsafeInputError
from open_ontology_lite.models import Ontology

MAX_FILE_SIZE = 2_000_000
MAX_NESTING_DEPTH = 40
MAX_INPUT_NODES = 100_000


class _DuplicateJsonKeyError(ValueError):
    """Raised internally when JSON contains an ambiguous duplicate key."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate keys in the same mapping."""


def _construct_unique_mapping(
    loader: yaml.SafeLoader, node: MappingNode, deep: bool = False
) -> dict[Any, Any]:
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = (
            (key_node.tag, key_node.value)
            if isinstance(key_node, ScalarNode) and key_node.tag == "tag:yaml.org,2002:merge"
            else loader.construct_object(key_node, deep=deep)
        )
        try:
            if key in seen:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a duplicate mapping key",
                    key_node.start_mark,
                )
            seen.add(key)
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_UniqueKeySafeLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError
        result[key] = value
    return result


def validation_error_message(exc: ValidationError) -> str:
    """Format Pydantic errors without echoing input values."""

    details = []
    for error in exc.errors(include_input=False):
        location = ".".join(str(part) for part in error["loc"]) or "<root>"
        details.append(f"{location}: {error['msg']}")
    return "; ".join(details)


def _yaml_error_message(exc: yaml.YAMLError) -> str:
    if isinstance(exc, yaml.MarkedYAMLError) and exc.problem_mark is not None:
        problem = exc.problem or "invalid YAML syntax"
        return (
            f"{problem} at line {exc.problem_mark.line + 1}, column {exc.problem_mark.column + 1}"
        )
    return "invalid YAML syntax"


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
    if path.is_symlink():
        raise UnsafeInputError(f"Symbolic links are not accepted as ontology input: {path}")
    try:
        path_stat = path.stat()
    except OSError as exc:
        raise OntologyLoadError(f"Cannot inspect ontology path: {path}") from exc
    if path.is_dir():
        raise OntologyLoadError(f"Ontology path is a directory: {path}")
    if not stat.S_ISREG(path_stat.st_mode):
        raise OntologyLoadError(f"Ontology path is not a regular file: {path}")
    if path_stat.st_size > MAX_FILE_SIZE:
        raise UnsafeInputError(f"Ontology file exceeds {MAX_FILE_SIZE} bytes: {path}")


def _read_bounded_utf8(path: Path) -> str:
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_FILE_SIZE + 1)
    except OSError as exc:
        raise OntologyLoadError(f"Cannot read ontology file: {path}") from exc
    if len(data) > MAX_FILE_SIZE:
        raise UnsafeInputError(f"Ontology file exceeds {MAX_FILE_SIZE} bytes: {path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OntologyParseError(f"Ontology file is not valid UTF-8: {path}") from exc


def _load_unique_yaml(text: str) -> object:
    loader = _UniqueKeySafeLoader(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()  # type: ignore[no-untyped-call]


def load_raw(path: str | Path) -> dict[str, Any]:
    """Load raw YAML or JSON using safe parsers."""

    source = Path(path)
    if not source.exists():
        raise OntologyLoadError(f"Ontology file not found: {source}")
    _ensure_safe_path(source)
    suffix = source.suffix.lower()
    text = _read_bounded_utf8(source)
    if not text.strip():
        raise OntologyParseError("Ontology file is empty.")
    try:
        if suffix in {".yaml", ".yml"}:
            loaded = _load_unique_yaml(text)
        elif suffix == ".json":
            loaded = json.loads(text, object_pairs_hook=_unique_json_object)
        else:
            raise OntologyLoadError(f"Unsupported ontology file extension: {suffix}")
    except yaml.YAMLError as exc:
        raise OntologyParseError(f"Malformed YAML: {_yaml_error_message(exc)}") from exc
    except _DuplicateJsonKeyError as exc:
        raise OntologyParseError("Malformed JSON: duplicate object key.") from exc
    except json.JSONDecodeError as exc:
        raise OntologyParseError(
            f"Malformed JSON at line {exc.lineno}, column {exc.colno}."
        ) from exc
    except RecursionError as exc:
        raise UnsafeInputError("Ontology input has excessive parser nesting.") from exc
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
        raise OntologyParseError(
            f"Invalid ontology structure: {validation_error_message(exc)}"
        ) from exc
