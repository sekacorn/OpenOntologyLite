# Changelog

## 0.2.0b2 - 2026-08-12

### Changed

- Recovery release containing the same Beta product functionality as the `0.2.0b1` candidate
  plus the corrected Trusted Publishing workflow. No product feature expansion occurred.
- `v0.2.0b1` remains an immutable tag whose publication failed before PyPI upload because the
  older pinned publisher action did not support Core Metadata 2.5.
- Updated the pinned PyPI publisher action for Core Metadata 2.5 compatibility.
- The public API and ontology schema remain compatible with the `0.1.x` Alpha line.
- Canonical ontology and AI System Map digests now normalize explicitly set-like
  declaration ordering while preserving free-form metadata ordering.
- Clarified that canonical digests support reproducibility and local locks only;
  they do not establish authorship, provenance, trust, factual accuracy, or runtime enforcement.

## 0.2.0b1 - 2026-08-12 (tagged, not published)

The immutable `v0.2.0b1` tag is retained for release-history accuracy. Its Trusted Publishing
workflow failed before upload because the pinned publisher action rejected Core Metadata 2.5.

## 0.1.0a4 - 2026-08-04

- Added bounded runtime entity-instance validation with aliases, defaults, nested values, references, safe decimal handling, and deterministic diagnostics.
- Added non-enforcing action-contract checks with input and output validation, permission gaps, unresolved preconditions, risk, review, escalation, audit expectations, and evidence paths.
- Added versioned neutral tool, policy, audit, meter, benchmark, and RAG handoff contracts with common ontology provenance.
- Added deterministic action JSON Schemas and machine-readable JSON and Markdown migration plans.
- Expanded AI System Maps with optional data, model, tool, review, retention, deployment, ontology-reference, and provenance fields.
- Added bounded local-only ontology imports with cycle, boundary, version, digest, namespace, conflict, and symlink defenses.
- Added runtime, contract, migration, and local-module CLI commands and a complete offline example.
- Hardened non-finite input handling, aggregate runtime limits, alias resolution, module version parsing, and generated-output path safety.
- Corrected structured enum diffs, migration paths, nested schema validation, scalar action outputs, and AI System Map sensitivity checks.

## 0.1.0a3 - 2026-07-26

- Added typed AI System Maps with semantic validation, deterministic Markdown reports, Mermaid rendering, and nested CLI commands.
- Added a fictional customer-support AI workload example with explicit routing, review, escalation, audit, cost, and integration-pattern meaning.
- Hardened untrusted input handling with bounded reads, duplicate-key rejection, sanitized diagnostics, terminal-safe validation output, and bounded AI-map issue retention.
- Repository maintenance: consolidated git commit authorship under a single maintainer identity (`sekacorn`).

## 0.1.0a2

- Added optional `aliases` fields for entities, properties, relationships, and actions.
- Added alias validation for stable ontology identifiers.
- Added rename-aware diff classification for alias-backed entity, relationship, and action renames.
- Added migration suggestions to diff changes.
- Bumped package version to `0.1.0a2`.

## 0.1.0a1

- Initial alpha implementation of OpenOntologyLite.
- YAML and JSON loading, validation, canonical normalization, digesting, inspection, cycle analysis, JSON Schema export, Mermaid export, Markdown documentation export, diffing, Python API, and CLI.
