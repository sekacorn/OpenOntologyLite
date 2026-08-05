# Ontology Format

The supported schema version is `1.0`. Files may be YAML or JSON and must contain `schema_version`, `ontology`, and at least one entity.

Entities contain typed properties. Supported property types are `string`, `integer`, `number`, `decimal`, `boolean`, `date`, `datetime`, `uuid`, `object`, `array`, and `reference`.

Object properties may declare nested `properties`. Arrays may use the existing primitive
`items` field or a recursive `items_schema`. Runtime validation bounds both forms.

Entities, properties, relationships, and actions may declare `aliases` to document previous stable identifiers during a rename. Aliases are validated as ontology identifiers and are used by diffing to classify explicit renames as migration events instead of unrelated removal/addition pairs.

Relationships declare `name`, `from`, `to`, and `cardinality`. Actions may additionally declare
risk, review, escalation, audit, and expected-audit-event metadata; they remain contracts and
are never executed. Permissions are named declarations with optional risk, tags, and metadata.

The optional top-level `imports` list declares local module paths, namespace expectations,
version constraints, and digest locks. Import resolution is explicit through
`resolve_local_modules`; ordinary `load_ontology` does not read imported files.
