"""Safe local ontology modules."""

from .models import ModuleProvenance, ResolvedOntology
from .resolver import resolve_local_modules

__all__ = ["ModuleProvenance", "ResolvedOntology", "resolve_local_modules"]
