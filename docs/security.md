# Security

OpenOntologyLite is local-first and offline. It does not use telemetry, databases, servers, AI models, credentials, remote references, or network calls for core functionality.

Ontology, local module, AI System Map, entity-instance, and action-input files are untrusted.
YAML uses a safe loader, duplicate YAML and JSON mapping keys are rejected, preconditions are
never executed, and user-controlled text is escaped or stripped of terminal control characters
at output boundaries.

The loader accepts direct regular files only and rejects symbolic links. It bounds the binary
read even if a file changes after inspection and enforces file-size, parsed-node,
parser-nesting, and structural-depth limits. Runtime validation also bounds strings,
collections, regular-expression input, recursion, and diagnostics. Diagnostics include types
and lengths where useful, not raw values.

CLI export commands reject invalid inputs before producing JSON Schema, Mermaid, or Markdown artifacts. AI System Map validation also bounds retained diagnostics, which prevents repeated invalid references from causing unbounded report memory growth.

Local imports are relative files confined to an explicit boundary. Resolution rejects remote
schemes, traversal, symlinks, cycles, duplicate namespaces, version mismatches, digest-lock
mismatches, excessive graph depth, excessive file count, and excessive aggregate bytes.
Decimal contracts reject binary floats; callers should use strings, integers, or
`decimal.Decimal` for exact values.
