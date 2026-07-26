# CLI Reference

Commands:

- `openontology validate <file>`
- `openontology inspect <file>`
- `openontology normalize <file>`
- `openontology digest <file>`
- `openontology cycles <file>`
- `openontology export-json-schema <file>`
- `openontology export-mermaid <file>`
- `openontology docs <file>`
- `openontology diff <old-file> <new-file>`
- `openontology ai-map validate <file>`
- `openontology ai-map report <file> [--format markdown]`
- `openontology ai-map render <file> [--format mermaid]`
- `openontology version`

Use `--help` on any command for command-specific flags.

Export commands validate the ontology before writing output. Invalid input exits nonzero and does not produce JSON Schema, Mermaid, or Markdown documentation.

AI System Map commands use the same exit convention:

- `0`: valid input and successful output;
- `1`: semantic validation failure, or warnings when `--strict` / `--fail-on-warning` is set;
- `2`: malformed input, unsupported format, or execution error.

`ai-map report` and `ai-map render` validate before writing. Reports and Mermaid source are deterministic for the same normalized map.
