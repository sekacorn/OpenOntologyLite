# OpenOntologyLite

OpenOntologyLite makes organizational meaning portable across AI models, agent frameworks, databases, and vendors.

## Status

Ready for public alpha release preparation with documented limitations.

## Alpha Warning

OpenOntologyLite is `0.1.0a2` alpha software. The format may evolve before stable 1.0, and diff classifications are conservative rule-based guidance rather than legal, operational, or authorization guarantees.

## Why It Exists

Organizations increasingly describe their work inside AI systems, agent frameworks, RAG stores, policy engines, and vendor platforms. OpenOntologyLite asks a practical question: can an organization move operational knowledge between systems without rebuilding the meaning of its business?

## Core Capabilities

- YAML and JSON ontology loading with safe parsers.
- Typed entities, properties, relationships, actions, permissions, and preconditions.
- Structural and semantic validation with stable machine-readable codes.
- Deterministic canonical JSON and SHA-256 digest generation.
- Cycle analysis for relationships and reference properties.
- JSON Schema 2020-12, Mermaid, Markdown documentation, inspection, and diff exports.
- Local-first operation with no telemetry, network calls, database, server, cloud account, or AI model requirement.

## Installation

```powershell
python -m pip install openontologylite
```

For development:

```powershell
python -m pip install -e ".[dev]"
```

## Quick Start

```powershell
openontology validate examples/customer_support.yaml
openontology inspect examples/customer_support.yaml
openontology digest examples/customer_support.yaml
openontology export-json-schema examples/customer_support.yaml --output build/customer-support.schema.json
openontology export-mermaid examples/customer_support.yaml --output build/customer-support.mmd
openontology docs examples/customer_support.yaml --output build/customer-support.md
```

## Example Ontology

```yaml
schema_version: "1.0"
ontology:
  id: customer-service
  name: Customer Service Ontology
  version: "1.0.0"
  namespace: example.customer_service
entities:
  Customer:
    properties:
      customer_id:
        type: string
        required: true
      account_status:
        type: string
        required: true
        enum: [active, suspended, closed]
```

## Python API

```python
from open_ontology_lite import load_ontology, validate_ontology, ontology_digest

ontology = load_ontology("examples/customer_support.yaml")
report = validate_ontology(ontology)
print(report.ok)
print(ontology_digest(ontology))
```

## Validation Example

Validation returns stable codes, messages, logical paths, suggestions, and context. Strict permission validation is the default; undeclared permissions fail unless non-strict mode is requested.

```powershell
openontology validate tests/fixtures/invalid/undeclared_permission.yaml --json
```

## Diff Example

```powershell
openontology diff tests/fixtures/diff/customer-support-v1.yaml tests/fixtures/diff/customer-support-v2.yaml
```

Diff exit behavior:

- `0`: no breaking changes detected;
- `1`: breaking changes detected;
- `2`: invalid input or execution error.

## JSON Schema Export

OpenOntologyLite exports deterministic JSON Schema 2020-12 documents. Some ontology semantics, such as actions, permissions, and relationship intent, are lossy in JSON Schema and are documented rather than represented as perfect round-trip data.

## Mermaid Export

The Mermaid command emits source text only. It does not require Mermaid to be installed.

## Ecosystem Position

OpenOntologyLite is designed to stand alone in the `0.1.0` alpha line while remaining friendly to later integrations with Forge, PrivateAIStack, ModelSwapBench, AgentPolicyPack, AIAuditLog, and OpenAIMeter.

## Security Model

Ontology files are untrusted input. The package uses safe YAML loading, size and nesting limits, non-executing preconditions, deterministic serialization, and escaping for Markdown and Mermaid outputs. It does not resolve remote schema references or execute expressions.

## Limitations

- No full RDF or OWL compatibility.
- No SPARQL.
- No general-purpose inference engine.
- No database synchronization.
- No graphical editor.
- No action execution.
- No authorization enforcement.
- Preconditions are declarative text only.
- No remote schema resolution.
- No hosted service.
- Diff classification is rule-based and conservative.
- JSON Schema export may be lossy for ontology-specific semantics.
- Relationship cycles are reported but not automatically invalid.
- Format may evolve before stable 1.0.

## Roadmap

`0.1.0a2`: aliases, rename-aware diffing, and migration hints.

`0.1.0a3`: additional exporters, stronger resource-limit configuration, Forge adapter, ModelSwapBench fixtures, PrivateAIStack RAG metadata, policy hooks for AgentPolicyPack.

`0.2`: optional SQLite catalog, ontology package imports, modular namespaces, signed manifests, provenance metadata.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run Ruff, mypy strict, pytest with branch coverage, Bandit, pip-audit, build, and Twine check before release preparation.

## License

MIT.

## Author

sekacorn
