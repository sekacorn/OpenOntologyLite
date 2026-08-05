# JSON Schema Export

JSON Schema export uses draft 2020-12 and emits deterministic JSON. Entity properties map to
JSON Schema properties, references accept a string/integer identifier or an expanded value from
local `$defs`, and date, datetime, and uuid use standard formats.

Nullable references are exported with `anyOf` so the local `$ref` remains valid while allowing
`null`. Exact `decimal` properties accept JSON integers or decimal strings. The exporter marks
them with `x-exact-decimal` and uses `x-minimum` / `x-maximum` where needed because standard
JSON Schema cannot apply numeric bounds to exact decimal strings without reintroducing
binary-float behavior.

Actions, permissions, and some relationship semantics do not round-trip through JSON Schema.
Action input and output schemas include local `$defs` and ontology identity metadata; no remote
references are generated.
