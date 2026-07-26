# Security

OpenOntologyLite is local-first and offline. It does not use telemetry, databases, servers, AI models, credentials, remote references, or network calls for core functionality.

Ontology and AI System Map files are untrusted. YAML uses a safe loader, duplicate YAML and JSON mapping keys are rejected, preconditions are never executed, and user-controlled text is escaped or stripped of terminal control characters at output boundaries.

The loader accepts regular files only, bounds the binary read even if a file changes after inspection, and enforces file-size, parsed-node, parser-nesting, and structural-depth limits. Structural diagnostics omit input values so malformed private data is not echoed back in errors.

CLI export commands reject invalid inputs before producing JSON Schema, Mermaid, or Markdown artifacts. AI System Map validation also bounds retained diagnostics, which prevents repeated invalid references from causing unbounded report memory growth.
