"""Smoke test the complete fictional example."""

from __future__ import annotations

import json
import runpy
from pathlib import Path


def test_complete_customer_support_example(capsys: object) -> None:
    root = Path(__file__).parents[1]
    runpy.run_path(
        str(root / "examples" / "customer_support_contracts.py"),
        run_name="__main__",
    )
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    summary = json.loads(output)
    assert summary["entity_valid"] is True
    assert summary["action_status"] == "satisfied"
    assert summary["shared_ontology_identity"] is True
    assert summary["ai_map_valid"] is True
