# Contributing

Thank you for helping improve OpenOntologyLite.

## Development Setup

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy --strict src
python -m pytest
python -m pytest --cov=open_ontology_lite --cov-branch
python -m bandit -r src
python -m pip_audit
python -m build
python -m twine check dist/*
```

Use `sekacorn` as the public author identity in release-facing files.

## Expectations

- Keep functionality deterministic by default.
- Treat ontology input as untrusted.
- Add tests for new validation codes, exporters, and CLI behavior.
- Do not add telemetry or network behavior to core functionality.
