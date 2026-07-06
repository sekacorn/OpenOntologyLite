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
- `openontology version`

Use `--help` on any command for command-specific flags.

Export commands validate the ontology before writing output. Invalid input exits nonzero and does not produce JSON Schema, Mermaid, or Markdown documentation.
