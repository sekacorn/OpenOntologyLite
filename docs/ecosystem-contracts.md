# Ecosystem Contracts

The `open_ontology_lite.contracts` package emits immutable, versioned, vendor-neutral handoff
objects. Every object carries a common ontology ID, version, namespace, and SHA-256 digest.

- `generate_tool_contract`: tool description with action input/output JSON Schema.
- `generate_policy_context`: request context for an external policy engine.
- `generate_audit_context`: ontology context for caller-managed audit events.
- `generate_meter_attribution`: allocation and outcome dimensions without cost calculation.
- `generate_benchmark_fixture`: task contract for an external benchmark runner.
- `generate_rag_metadata`: metadata for caller-managed document ingestion.

These functions transform meaning only. They do not import sibling packages, call networks,
register or execute tools, make policy decisions, persist audit data, calculate invoices,
execute benchmarks, or ingest documents.
