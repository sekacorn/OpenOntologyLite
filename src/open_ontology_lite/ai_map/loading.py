"""Loading and canonical digest helpers for AI System Maps."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from open_ontology_lite.ai_map.models import AISystemMap
from open_ontology_lite.errors import OntologyParseError
from open_ontology_lite.loading.loader import load_raw, validation_error_message

_UNORDERED_TASK_FIELDS = frozenset({"allowed_routes", "escalation"})


def load_ai_system_map(path: str | Path) -> AISystemMap:
    """Load an AI System Map from bounded YAML or JSON input."""

    raw = load_raw(path)
    try:
        return AISystemMap.model_validate(raw)
    except ValidationError as exc:
        raise OntologyParseError(
            f"Invalid AI System Map structure: {validation_error_message(exc)}"
        ) from exc


def canonical_ai_system_map_json(ai_map: AISystemMap) -> str:
    """Return stable JSON suitable for hashing and reproducibility checks."""

    data = ai_map.model_dump(mode="json")
    for task in data["tasks"]:
        for field in _UNORDERED_TASK_FIELDS:
            task[field] = sorted(task[field])
    for key in ("entities", "tasks", "model_routes", "escalation_paths", "integrations"):
        sort_key = "tool" if key == "integrations" else "name"
        data[key] = sorted(data[key], key=lambda item: item[sort_key].casefold())
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"


def ai_system_map_digest(ai_map: AISystemMap) -> str:
    """Return the canonical SHA-256 digest for an AI System Map."""

    return hashlib.sha256(canonical_ai_system_map_json(ai_map).encode("utf-8")).hexdigest()
