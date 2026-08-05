"""Exception hierarchy for OpenOntologyLite."""


class OpenOntologyLiteError(Exception):
    """Base exception for OpenOntologyLite."""


class OntologyLoadError(OpenOntologyLiteError):
    """Raised when an ontology file cannot be loaded."""


class OntologyParseError(OntologyLoadError):
    """Raised when YAML or JSON parsing fails."""


class OntologyValidationError(OpenOntologyLiteError):
    """Raised when ontology validation fails."""


class OntologyExportError(OpenOntologyLiteError):
    """Raised when export generation fails."""


class OntologyDiffError(OpenOntologyLiteError):
    """Raised when ontology diffing fails."""


class UnsafeInputError(OpenOntologyLiteError):
    """Raised when input exceeds safety limits or contains unsafe content."""


class UnsupportedSchemaVersionError(OntologyValidationError):
    """Raised when the ontology schema version is unsupported."""


class ModuleResolutionError(OpenOntologyLiteError):
    """Raised when a local ontology import graph cannot be resolved safely."""
