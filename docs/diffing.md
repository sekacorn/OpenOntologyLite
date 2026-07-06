# Diffing

Diffing classifies changes as `breaking`, `potentially_breaking`, `non_breaking`, or `informational`.

When a new entity, relationship, or action declares an old identifier in `aliases`, diffing reports an explicit rename such as `ENTITY_RENAMED`, `RELATIONSHIP_RENAMED`, or `ACTION_RENAMED`. These are classified as potentially breaking because downstream consumers may still need migration work.

The CLI exits `0` when no breaking changes are detected, `1` when breaking changes are detected, and `2` for invalid input or execution errors.
