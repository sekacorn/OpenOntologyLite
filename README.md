# OpenOntologyLite

OpenOntologyLite is a lightweight, executable semantic-contract toolkit for defining and
validating organizational entities, relationships, actions, permissions, and AI workloads
across models, agents, databases, and vendors.

## Status

Current candidate: `0.2.0b1`, the first Beta release candidate with documented limitations.

## Beta Candidate Notice

OpenOntologyLite is `0.2.0b1` Beta-candidate software. It provides deterministic validation
and contract transformation, but remains under active compatibility review. It does not execute
actions, enforce authorization, or perform general-purpose inference.

## Why It Exists

Organizations increasingly describe their work inside AI systems, agent frameworks, RAG stores, policy engines, and vendor platforms. OpenOntologyLite asks a practical question: can an organization move operational knowledge between systems without rebuilding the meaning of its business?

## Core Capabilities

- YAML and JSON ontology loading with safe parsers.
- Typed entities, properties, relationships, actions, permissions, and preconditions.
- Runtime entity-instance validation and non-enforcing action-contract checks.
- Versioned neutral tool, policy, audit, meter, benchmark, and RAG handoff contracts.
- Structural and semantic validation with stable machine-readable codes.
- Deterministic canonical JSON and SHA-256 digest generation.
- Cycle analysis for relationships and reference properties.
- JSON Schema 2020-12, Mermaid, Markdown documentation, inspection, and diff exports.
- Typed AI System Maps for workload risk, model routes, review, escalation, audit, and cost expectations.
- Deterministic migration plans and bounded local-only ontology modules.
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
openontology entity validate examples/customer_support.yaml Customer examples/data/customer.json --json
openontology action check examples/customer_support.yaml create_ticket examples/data/create_ticket.json -p support.ticket.create --json
openontology contract tool examples/customer_support.yaml create_ticket
openontology migration-plan old.yaml new.yaml --format markdown
```

AI workload mapping:

```powershell
openontology ai-map validate examples/ai_system_map/customer_support_ai.yaml
openontology ai-map report examples/ai_system_map/customer_support_ai.yaml --output build/customer-support-ai.md
openontology ai-map render examples/ai_system_map/customer_support_ai.yaml --format mermaid --output build/customer-support-ai.mmd
```

Use `--strict` or `--fail-on-warning` when warnings must also produce a nonzero exit. See [AI System Maps](docs/ai-system-map.md) for the format and control rules.

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
from open_ontology_lite import (
    check_action_contract,
    generate_tool_contract,
    load_ontology,
    validate_entity_instance,
)

ontology = load_ontology("examples/customer_support.yaml")
entity = validate_entity_instance(
    ontology,
    entity_type="Customer",
    value={"customer_id": "C-1042"},
)
action = check_action_contract(
    ontology,
    action="create_ticket",
    inputs={"customer_id": "C-1042", "description": "Cannot sign in"},
    actor_permissions=["support.ticket.create"],
)
tool = generate_tool_contract(ontology, "create_ticket")
print(entity.valid, action.status, tool.name)
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

## AI System Maps

An AI System Map records the portable business meaning of AI work: named tasks and entities, risk levels, permitted model routes, human-review and escalation requirements, expected audit events, expected cost/outcome metrics, and integration patterns. It is a declarative artifact, not a runtime router, compliance certification, or policy enforcement engine.

The route vocabulary is intentionally small: `candidate_model`, `baseline_model`, `human_review`, and `blocked_or_escalate`. Risk levels are `low`, `medium`, `high`, `regulated`, and `unknown`.

```yaml
schema_version: "1.0"
system:
  name: Customer Support AI
  risk_profile: medium
tasks:
  - name: PasswordReset
    risk_level: low
    allowed_routes: [candidate_model, baseline_model]
    expected_audit_events: [route_selected]
    expected_metrics: [estimated_cost, resolution_outcome]
```

## Ecosystem Position

OpenOntologyLite remains independently installable. Its neutral contracts can be consumed by
adapters for AgentForge, PrivateAIStack, ModelSwapBench, AgentPolicyPack, AIAuditLog, and
AIMeter OSS, but generation does not claim registration, execution, persistence, enforcement,
ingestion, billing, or a verified live integration.

## Security Model

Ontology, module, AI System Map, entity, and action files are untrusted input. The package uses
bounded regular-file reads, symlink rejection, safe YAML loading, duplicate-key rejection,
graph, parsed-node, collection, string, nesting, and diagnostic limits, non-executing
preconditions, deterministic serialization, and sanitized diagnostics. It does not resolve
remote imports or schema references, execute expressions, or run shell commands.

## Limitations

- No full RDF or OWL compatibility.
- No SPARQL.
- No general-purpose inference engine.
- No database synchronization.
- No graphical editor.
- No action execution.
- No final authorization or policy-enforcement decisions.
- Preconditions are declarative text only.
- No remote schema resolution.
- No hosted service.
- AI System Maps document intended controls but do not execute routing, review, audit, or cost enforcement.
- Neutral contracts do not register Forge tools, write audit records, calculate invoices or
  realized savings, execute benchmarks, or ingest RAG documents.
- No compliance certification.
- Diff classification is rule-based and conservative.
- JSON Schema export may be lossy for ontology-specific semantics.
- Relationship cycles are reported but not automatically invalid.
- Format may evolve before stable 1.0.

## Roadmap

Current Beta candidate, `0.2.0b1`:

- Added runtime entity and action validation, neutral ecosystem contracts, action schemas, and
  deterministic migration planning.
- Expanded AI System Maps and added safe local module foundations with provenance.
- Normalized canonical ordering for explicitly set-like declarations and clarified digest limits.

After Beta:

- Additional contract adapters and resource-limit configuration.
- Broader local module composition and schema packaging.

Deferred post-Beta work:

- Optional SQLite catalog.
- Signed manifests.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run Ruff, mypy strict, pytest with branch coverage, Bandit, pip-audit, build, and Twine check before release preparation.

## License

[Apache License 2.0](LICENSE).

## Author

sekacorn
