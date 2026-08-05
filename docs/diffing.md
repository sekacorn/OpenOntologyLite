# Diffing

Diffing classifies changes as `breaking`, `potentially_breaking`, `non_breaking`, or `informational`.

When a new entity, relationship, or action declares an old identifier in `aliases`, diffing reports an explicit rename such as `ENTITY_RENAMED`, `RELATIONSHIP_RENAMED`, or `ACTION_RENAMED`. These are classified as potentially breaking because downstream consumers may still need migration work.

The CLI exits `0` when no breaking changes are detected, `1` when breaking changes are detected, and `2` for invalid input or execution errors.

## Migration Plans

`build_migration_plan(old, new)` transforms the conservative diff into typed guidance with old
and new logical paths, alias availability, an explicit migration recommendation, automation
safety, evidence, and suggested semantic-version impact. It does not rewrite ontologies or
business data.

```powershell
openontology migration-plan old.yaml new.yaml --format json
openontology migration-plan old.yaml new.yaml --format markdown
```

Plans cover renames, removals, required additions, type/default/constraint changes,
relationship source, target, and cardinality changes, action input/output, permission, risk,
review, namespace, and identity changes. Output ordering is deterministic.
