# Security

OpenOntologyLite is local-first and offline. It does not use telemetry, databases, servers, AI models, credentials, remote references, or network calls for core functionality.

Ontology files are untrusted. YAML uses safe loading, preconditions are never executed, and user-controlled text is escaped in Markdown and Mermaid exports.

The loader enforces file-size, parsed-node, and nesting-depth limits before model validation. CLI export commands reject invalid ontologies before producing JSON Schema, Mermaid, or Markdown artifacts, which reduces the chance of exporting malformed references or unsafe labels from invalid input.
