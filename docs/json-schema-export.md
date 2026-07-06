# JSON Schema Export

JSON Schema export uses draft 2020-12 and emits deterministic JSON. Entity properties map to JSON Schema properties, references map to local `$defs`, and date, datetime, and uuid use standard formats.

Actions, permissions, and some relationship semantics do not round-trip through JSON Schema.
