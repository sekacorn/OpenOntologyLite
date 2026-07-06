"""Identifier and text safety validation."""

from __future__ import annotations

import re

IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
NAMESPACE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$")
PERMISSION_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
MAX_TEXT_LENGTH = 10_000
MAX_PRECONDITION_LENGTH = 1_000


def is_identifier(value: str) -> bool:
    """Return whether a value is a stable ontology identifier."""

    return bool(IDENTIFIER_RE.fullmatch(value))


def is_namespace(value: str) -> bool:
    """Return whether a namespace is syntactically valid."""

    return bool(NAMESPACE_RE.fullmatch(value))


def is_permission_name(value: str) -> bool:
    """Return whether a permission declaration name is syntactically valid."""

    return bool(PERMISSION_RE.fullmatch(value))


def has_control_characters(value: str) -> bool:
    """Return whether text contains unsafe control characters."""

    return any((ord(ch) < 32 and ch not in "\t\n\r") or ord(ch) == 127 for ch in value)
