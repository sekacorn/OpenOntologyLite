# Ontology Format

The supported schema version is `1.0`. Files may be YAML or JSON and must contain `schema_version`, `ontology`, and at least one entity.

Entities contain typed properties. Supported property types are `string`, `integer`, `number`, `decimal`, `boolean`, `date`, `datetime`, `uuid`, `object`, `array`, and `reference`.

Entities, properties, relationships, and actions may declare `aliases` to document previous stable identifiers during a rename. Aliases are validated as ontology identifiers and are used by diffing to classify explicit renames as migration events instead of unrelated removal/addition pairs.

Relationships declare `name`, `from`, `to`, and `cardinality`. Actions declare operation contracts but are not executed. Permissions are named declarations with optional risk, tags, and metadata.
