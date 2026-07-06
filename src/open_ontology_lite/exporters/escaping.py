"""Escaping helpers for untrusted ontology text."""

from __future__ import annotations

import html
import re


def plain(value: object) -> str:
    """Return terminal-safe plain text."""

    text = str(value)
    return "".join(ch if (ord(ch) >= 32 and ord(ch) != 127) else " " for ch in text)


def markdown(value: object) -> str:
    """Escape Markdown table and control-sensitive characters."""

    text = plain(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
    return re.sub(r"([*_`<>])", r"\\\1", text)


def mermaid(value: object) -> str:
    """Escape Mermaid label text."""

    text = (
        plain(value)
        .replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("{", "(")
        .replace("}", ")")
    )
    return html.escape(text, quote=False)
