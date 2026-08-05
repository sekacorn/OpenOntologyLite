"""Bounded, local-only ontology module resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from open_ontology_lite.errors import ModuleResolutionError, UnsafeInputError
from open_ontology_lite.loading import load_ontology
from open_ontology_lite.models import Ontology, PropertyDef
from open_ontology_lite.normalization import ontology_digest
from open_ontology_lite.validation import validate_ontology

from .models import ModuleProvenance, ResolvedOntology

MAX_IMPORTS = 32
MAX_IMPORT_DEPTH = 8
MAX_IMPORT_BYTES = 16_000_000
_REMOTE_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_VERSION_PART = re.compile(r"^(>=|<=|==|>|<)?\s*([0-9]+(?:\.[0-9]+){0,2})$")


@dataclass
class _State:
    boundary: Path
    paths: set[Path]
    active: set[Path]
    ontologies: list[tuple[Path, Ontology]]
    total_bytes: int = 0


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?", value)
    if match is None:
        raise ModuleResolutionError(f"Unsupported module version: {value}")
    major, minor, patch = match.groups()
    return int(major), int(minor or 0), int(patch or 0)


def _version_matches(version: str, constraint: str | None) -> bool:
    if not constraint:
        return True
    current = _version_tuple(version)
    for raw_part in constraint.split(","):
        match = _VERSION_PART.fullmatch(raw_part.strip())
        if match is None:
            raise ModuleResolutionError(f"Unsupported version constraint: {constraint}")
        operator, expected_text = match.groups()
        expected = _version_tuple(expected_text)
        comparisons = {
            None: current == expected,
            "==": current == expected,
            ">=": current >= expected,
            "<=": current <= expected,
            ">": current > expected,
            "<": current < expected,
        }
        if not comparisons[operator]:
            return False
    return True


def _inside(path: Path, boundary: Path) -> bool:
    try:
        path.relative_to(boundary)
    except ValueError:
        return False
    return True


def _visit(path: Path, state: _State, depth: int) -> None:
    if depth > MAX_IMPORT_DEPTH:
        raise UnsafeInputError(f"Ontology import depth exceeds {MAX_IMPORT_DEPTH}.")
    resolved = path.resolve(strict=True)
    if not _inside(resolved, state.boundary):
        raise ModuleResolutionError("Ontology import leaves the configured filesystem boundary.")
    if path.is_symlink() or resolved.is_symlink():
        raise UnsafeInputError("Symbolic links are not accepted in ontology imports.")
    if resolved in state.active:
        raise ModuleResolutionError("Ontology import cycle detected.")
    if resolved in state.paths:
        return
    if len(state.paths) >= MAX_IMPORTS:
        raise UnsafeInputError(f"Ontology import graph exceeds {MAX_IMPORTS} files.")
    state.total_bytes += resolved.stat().st_size
    if state.total_bytes > MAX_IMPORT_BYTES:
        raise UnsafeInputError(f"Ontology import graph exceeds {MAX_IMPORT_BYTES} bytes.")
    ontology = load_ontology(resolved)
    if validate_ontology(ontology).errors:
        raise ModuleResolutionError("An ontology module failed semantic validation.")
    state.paths.add(resolved)
    state.active.add(resolved)
    state.ontologies.append((resolved, ontology))
    for declaration in ontology.imports:
        if _REMOTE_SCHEME.match(declaration.path):
            raise ModuleResolutionError("Remote ontology imports are not supported.")
        child = resolved.parent / declaration.path
        _visit(child, state, depth + 1)
        child_ontology = next(
            item for item_path, item in state.ontologies if item_path == child.resolve()
        )
        if declaration.namespace and declaration.namespace != child_ontology.ontology.namespace:
            raise ModuleResolutionError(
                "Imported ontology namespace does not match its declaration."
            )
        if not _version_matches(child_ontology.ontology.version, declaration.version):
            raise ModuleResolutionError(
                "Imported ontology version does not satisfy its constraint."
            )
        if declaration.digest and declaration.digest != ontology_digest(child_ontology):
            raise ModuleResolutionError("Imported ontology digest does not match its lock.")
    state.active.remove(resolved)


def _prefix(namespace: str) -> str:
    return namespace.replace(".", "__").casefold()


def _property_refs(prop: PropertyDef, entity_names: set[str], prefix: str) -> PropertyDef:
    target = f"{prefix}__{prop.target}" if prop.target in entity_names else prop.target
    properties = {
        name: _property_refs(value, entity_names, prefix) for name, value in prop.properties.items()
    }
    items_schema = (
        _property_refs(prop.items_schema, entity_names, prefix) if prop.items_schema else None
    )
    return prop.model_copy(
        update={"target": target, "properties": properties, "items_schema": items_schema}
    )


def _merge(root: Ontology, modules: list[tuple[Path, Ontology]]) -> tuple[Ontology, dict[str, str]]:
    entities = dict(root.entities)
    relationships = list(root.relationships)
    actions = list(root.actions)
    permissions = dict(root.permissions)
    provenance = {
        **{f"entities.{name}": root.ontology.namespace for name in root.entities},
        **{
            f"relationships.{relation.name}": root.ontology.namespace
            for relation in root.relationships
        },
        **{f"actions.{action.name}": root.ontology.namespace for action in root.actions},
        **{f"permissions.{name}": root.ontology.namespace for name in root.permissions},
    }
    relationship_names = {relation.name for relation in relationships}
    action_names = {action.name for action in actions}
    namespaces = {root.ontology.namespace}
    for _, module in sorted(modules[1:], key=lambda item: item[1].ontology.namespace):
        namespace = module.ontology.namespace
        if namespace in namespaces:
            raise ModuleResolutionError(f"Duplicate imported namespace: {namespace}")
        namespaces.add(namespace)
        prefix = _prefix(namespace)
        entity_names = set(module.entities)
        permission_names = set(module.permissions)
        for name, entity in sorted(module.entities.items()):
            qualified = f"{prefix}__{name}"
            if qualified in entities:
                raise ModuleResolutionError(f"Conflicting entity definition: {qualified}")
            properties = {
                prop_name: _property_refs(prop, entity_names, prefix)
                for prop_name, prop in entity.properties.items()
            }
            entities[qualified] = entity.model_copy(
                update={"id": qualified, "name": qualified, "properties": properties}
            )
            provenance[f"entities.{qualified}"] = namespace
        for relation in sorted(module.relationships, key=lambda item: item.name):
            qualified = f"{prefix}__{relation.name}"
            if qualified in relationship_names:
                raise ModuleResolutionError(f"Conflicting relationship definition: {qualified}")
            relationship_names.add(qualified)
            relationships.append(
                relation.model_copy(
                    update={
                        "name": qualified,
                        "from_": f"{prefix}__{relation.from_}",
                        "to": f"{prefix}__{relation.to}",
                    }
                )
            )
            provenance[f"relationships.{qualified}"] = namespace
        for action in sorted(module.actions, key=lambda item: item.name):
            qualified = f"{prefix}__{action.name}"
            if qualified in action_names:
                raise ModuleResolutionError(f"Conflicting action definition: {qualified}")
            action_names.add(qualified)
            action_inputs = {
                name: _property_refs(prop, entity_names, prefix)
                for name, prop in action.inputs.items()
            }
            output = _property_refs(action.output, entity_names, prefix) if action.output else None
            action_permissions = tuple(
                f"{prefix}.{permission}" if permission in permission_names else permission
                for permission in action.permissions
            )
            actions.append(
                action.model_copy(
                    update={
                        "name": qualified,
                        "subject": f"{prefix}__{action.subject}",
                        "inputs": action_inputs,
                        "output": output,
                        "permissions": action_permissions,
                    }
                )
            )
            provenance[f"actions.{qualified}"] = namespace
        for name, permission in sorted(module.permissions.items()):
            qualified = f"{prefix}.{name}"
            if qualified in permissions:
                raise ModuleResolutionError(f"Conflicting permission definition: {qualified}")
            permissions[qualified] = permission
            provenance[f"permissions.{qualified}"] = namespace
    return (
        root.model_copy(
            update={
                "entities": entities,
                "relationships": tuple(relationships),
                "actions": tuple(actions),
                "permissions": permissions,
                "imports": (),
            }
        ),
        provenance,
    )


def resolve_local_modules(
    path: str | Path, *, boundary: str | Path | None = None
) -> ResolvedOntology:
    """Resolve and merge a bounded graph of explicit local ontology imports."""

    root_path = Path(path)
    root_boundary = Path(boundary).resolve() if boundary else root_path.resolve().parent
    state = _State(boundary=root_boundary, paths=set(), active=set(), ontologies=[])
    _visit(root_path, state, 0)
    root = state.ontologies[0][1]
    merged, provenance = _merge(root, state.ontologies)
    modules = tuple(
        ModuleProvenance(
            namespace=ontology.ontology.namespace,
            version=ontology.ontology.version,
            digest=ontology_digest(ontology),
            path=path.relative_to(root_boundary).as_posix(),
        )
        for path, ontology in sorted(state.ontologies, key=lambda item: item[1].ontology.namespace)
    )
    return ResolvedOntology(ontology=merged, modules=modules, provenance=provenance)
