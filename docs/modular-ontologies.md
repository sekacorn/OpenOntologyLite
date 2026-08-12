# Modular Ontologies

`resolve_local_modules(path, boundary=...)` resolves explicit local `imports` and returns a
merged ontology, module digests, repo-relative provenance paths, and definition provenance.
Imported definitions use deterministic namespace-qualified identifiers.

```yaml
imports:
  - path: modules/shared.yaml
    namespace: example.shared
    version: ">=1.0,<2.0"
    digest: optional_sha256_lock
```

The resolver is intentionally not a package manager. Imports cannot be remote, escape the
filesystem boundary, follow symbolic links, execute code, or exceed graph limits. Cycles,
duplicate namespaces, conflicting declarations, unsupported version expressions, and digest
mismatches fail closed.

For this Beta candidate, every imported file must be semantically valid on its own. Cross-module
references and module-level override rules are deferred; the resolver composes independent
modules and reports provenance without acting as a dependency registry.
