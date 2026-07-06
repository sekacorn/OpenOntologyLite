# Security

OpenOntologyLite is local-first and offline. It does not use telemetry, databases, servers, AI models, credentials, remote references, or network calls for core functionality.

Ontology files are untrusted. YAML uses safe loading, preconditions are never executed, and user-controlled text is escaped in Markdown and Mermaid exports.
