# JSON Schema Export

JSON Schema export uses draft 2020-12 and emits deterministic JSON. Entity properties map to JSON Schema properties, references map to local `$defs`, and date, datetime, and uuid use standard formats.

Nullable references are exported with `anyOf` so the local `$ref` remains valid while allowing `null`. Decimal values are serialized deterministically as strings when JSON itself cannot represent them safely.

Actions, permissions, and some relationship semantics do not round-trip through JSON Schema.
