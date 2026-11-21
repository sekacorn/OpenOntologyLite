# JSON-LD export

`openontology export-json-ld SOURCE --output ontology.jsonld` writes a deterministic `openontologylite.jsonld.v1` document. The envelope follows JSON-LD 1.1 syntax and carries the complete normalized OpenOntologyLite ontology under `ontology`.

`load_json_ld(path)` validates the envelope and reconstructs the immutable `Ontology` model. A round trip preserves `ontology_digest`. This format provides an open, self-describing transfer document for OpenOntologyLite. It does not claim general RDF, OWL, SPARQL, or third-party ontology-tool compatibility.

The packaged `schemas/json-ld-v1.schema.json` validates the envelope. OpenOntologyLite performs the complete nested ontology validation when loading.
