"""Ontology diff engine."""

from __future__ import annotations

from open_ontology_lite.models import Ontology
from open_ontology_lite.models.diff import DiffChange, DiffResult


def _change(
    classification: str,
    code: str,
    path: str,
    message: str,
    suggestion: str | None = None,
) -> DiffChange:
    return DiffChange(
        classification=classification,  # type: ignore[arg-type]
        code=code,
        path=path,
        message=message,
        suggestion=suggestion,
    )


def _alias_renames(
    removed: set[str], added: set[str], aliases_by_new_name: dict[str, tuple[str, ...]]
) -> dict[str, str]:
    # Treat a removed name as a rename only when a new declaration explicitly
    # carries it as an alias; this keeps ordinary remove/add pairs conservative.
    renames: dict[str, str] = {}
    for new_name in sorted(added):
        for alias in aliases_by_new_name.get(new_name, ()):
            if alias in removed and alias not in renames:
                renames[alias] = new_name
                break
    return renames


def diff_ontologies(old: Ontology, new: Ontology) -> DiffResult:
    """Compare two ontologies using conservative rule-based classification."""

    changes: list[DiffChange] = []
    if old.ontology.id != new.ontology.id:
        changes.append(
            _change(
                "breaking",
                "ONTOLOGY_ID_CHANGED",
                "ontology.id",
                f"Ontology identity changed from '{old.ontology.id}' to '{new.ontology.id}'.",
            )
        )
    if old.ontology.namespace != new.ontology.namespace:
        changes.append(
            _change(
                "potentially_breaking",
                "ONTOLOGY_NAMESPACE_CHANGED",
                "ontology.namespace",
                "Ontology namespace changed.",
                "Update namespace-qualified references in downstream contracts.",
            )
        )
    old_entities = set(old.entities)
    new_entities = set(new.entities)

    # Entity aliases let maintainers document intentional renames while still
    # surfacing migration work as potentially breaking.
    entity_renames = _alias_renames(
        old_entities - new_entities,
        new_entities - old_entities,
        {name: entity.aliases for name, entity in new.entities.items()},
    )
    for old_name, new_name in sorted(entity_renames.items()):
        changes.append(
            _change(
                "potentially_breaking",
                "ENTITY_RENAMED",
                f"entities.{new_name}.aliases",
                f"Entity '{old_name}' appears to have been renamed to '{new_name}'.",
                "Keep the alias until downstream consumers migrate to the new entity name.",
            )
        )
    for entity in sorted((old_entities - new_entities) - set(entity_renames)):
        changes.append(
            _change(
                "breaking",
                "ENTITY_REMOVED",
                f"entities.{entity}",
                f"Entity '{entity}' was removed.",
            )
        )
    for entity in sorted((new_entities - old_entities) - set(entity_renames.values())):
        changes.append(
            _change(
                "non_breaking",
                "ENTITY_ADDED",
                f"entities.{entity}",
                f"Entity '{entity}' was added.",
            )
        )
    for entity in sorted(old_entities & new_entities):
        old_props = old.entities[entity].properties
        new_props = new.entities[entity].properties
        # Property rename detection is scoped to an unchanged entity; entity
        # rename migration is reported separately above.
        prop_renames = _alias_renames(
            set(old_props) - set(new_props),
            set(new_props) - set(old_props),
            {name: prop.aliases for name, prop in new_props.items()},
        )
        for old_name, new_name in sorted(prop_renames.items()):
            changes.append(
                _change(
                    "potentially_breaking",
                    "PROPERTY_RENAMED",
                    f"entities.{entity}.properties.{new_name}.aliases",
                    f"Property '{old_name}' appears to have been renamed to '{new_name}'.",
                    "Keep the alias until readers and writers use the new property name.",
                )
            )
        for prop in sorted((set(old_props) - set(new_props)) - set(prop_renames)):
            classification = "breaking" if old_props[prop].required else "potentially_breaking"
            changes.append(
                _change(
                    classification,
                    "PROPERTY_REMOVED",
                    f"entities.{entity}.properties.{prop}",
                    f"Property '{prop}' was removed from '{entity}'.",
                )
            )
        for prop in sorted((set(new_props) - set(old_props)) - set(prop_renames.values())):
            new_prop = new_props[prop]
            if new_prop.required and new_prop.default is None:
                changes.append(
                    _change(
                        "breaking",
                        "REQUIRED_PROPERTY_ADDED",
                        f"entities.{entity}.properties.{prop}",
                        f"Required property '{prop}' was added without a default.",
                    )
                )
            elif new_prop.required:
                changes.append(
                    _change(
                        "potentially_breaking",
                        "REQUIRED_PROPERTY_ADDED_WITH_DEFAULT",
                        f"entities.{entity}.properties.{prop}",
                        f"Required property '{prop}' was added with a default.",
                    )
                )
            else:
                changes.append(
                    _change(
                        "non_breaking",
                        "OPTIONAL_PROPERTY_ADDED",
                        f"entities.{entity}.properties.{prop}",
                        f"Optional property '{prop}' was added.",
                    )
                )
        for prop in sorted(set(old_props) & set(new_props)):
            old_prop = old_props[prop]
            new_prop = new_props[prop]
            path = f"entities.{entity}.properties.{prop}"
            if old_prop.type != new_prop.type:
                changes.append(
                    _change(
                        "breaking",
                        "PROPERTY_TYPE_CHANGED",
                        path,
                        f"Property '{prop}' changed type from {old_prop.type} to {new_prop.type}.",
                    )
                )
            if old_prop.default != new_prop.default:
                changes.append(
                    _change(
                        "potentially_breaking",
                        "PROPERTY_DEFAULT_CHANGED",
                        path,
                        f"Default for '{prop}' changed.",
                    )
                )
            if old_prop.enum is not None and new_prop.enum is not None:
                removed = set(old_prop.enum) - set(new_prop.enum)
                added = set(new_prop.enum) - set(old_prop.enum)
                if removed:
                    changes.append(
                        _change(
                            "breaking",
                            "ENUM_VALUE_REMOVED",
                            path,
                            f"Enum values removed from '{prop}': {sorted(removed)}.",
                        )
                    )
                if added:
                    changes.append(
                        _change(
                            "non_breaking",
                            "ENUM_VALUE_ADDED",
                            path,
                            f"Enum values added to '{prop}': {sorted(added)}.",
                        )
                    )
            if old_prop.required is False and new_prop.required is True:
                classification = (
                    "potentially_breaking" if new_prop.default is not None else "breaking"
                )
                changes.append(
                    _change(
                        classification,
                        "PROPERTY_BECAME_REQUIRED",
                        path,
                        f"Property '{prop}' became required.",
                    )
                )
            if (
                old_prop.minimum is not None
                and new_prop.minimum is not None
                and new_prop.minimum > old_prop.minimum
            ):
                changes.append(
                    _change(
                        "potentially_breaking",
                        "NUMERIC_LIMIT_STRICTER",
                        path,
                        f"Minimum for '{prop}' became stricter.",
                    )
                )
            if (
                old_prop.maximum is not None
                and new_prop.maximum is not None
                and new_prop.maximum < old_prop.maximum
            ):
                changes.append(
                    _change(
                        "potentially_breaking",
                        "NUMERIC_LIMIT_STRICTER",
                        path,
                        f"Maximum for '{prop}' became stricter.",
                    )
                )
            if (
                old_prop.minimum is not None
                and new_prop.minimum is not None
                and new_prop.minimum < old_prop.minimum
            ) or (
                old_prop.maximum is not None
                and new_prop.maximum is not None
                and new_prop.maximum > old_prop.maximum
            ):
                changes.append(
                    _change(
                        "non_breaking",
                        "NUMERIC_LIMIT_RELAXED",
                        path,
                        f"Numeric limits for '{prop}' were relaxed.",
                    )
                )
            if (
                old_prop.min_length is not None
                and new_prop.min_length is not None
                and new_prop.min_length > old_prop.min_length
            ) or (
                old_prop.max_length is not None
                and new_prop.max_length is not None
                and new_prop.max_length < old_prop.max_length
            ):
                changes.append(
                    _change(
                        "potentially_breaking",
                        "LENGTH_LIMIT_STRICTER",
                        path,
                        f"Length limits for '{prop}' became stricter.",
                    )
                )
            if (
                old_prop.min_length is not None
                and new_prop.min_length is not None
                and new_prop.min_length < old_prop.min_length
            ) or (
                old_prop.max_length is not None
                and new_prop.max_length is not None
                and new_prop.max_length > old_prop.max_length
            ):
                changes.append(
                    _change(
                        "non_breaking",
                        "LENGTH_LIMIT_RELAXED",
                        path,
                        f"Length limits for '{prop}' were relaxed.",
                    )
                )
            if old_prop.pattern != new_prop.pattern and old_prop.pattern is not None:
                changes.append(
                    _change(
                        "potentially_breaking",
                        "PATTERN_CHANGED",
                        path,
                        f"Pattern for '{prop}' changed.",
                    )
                )
            if old_prop.description != new_prop.description:
                changes.append(
                    _change(
                        "non_breaking",
                        "DESCRIPTION_CHANGED",
                        path,
                        f"Description for '{prop}' changed.",
                    )
                )

    old_rels = {rel.name: rel for rel in old.relationships}
    new_rels = {rel.name: rel for rel in new.relationships}
    # Relationships and actions are list-backed in the ontology model, so map
    # them by stable name before comparing versions.
    relationship_renames = _alias_renames(
        set(old_rels) - set(new_rels),
        set(new_rels) - set(old_rels),
        {name: rel.aliases for name, rel in new_rels.items()},
    )
    for old_name, new_name in sorted(relationship_renames.items()):
        changes.append(
            _change(
                "potentially_breaking",
                "RELATIONSHIP_RENAMED",
                f"relationships.{new_name}.aliases",
                f"Relationship '{old_name}' appears to have been renamed to '{new_name}'.",
                "Keep the alias until relationship consumers migrate to the new name.",
            )
        )
    for name in sorted((set(old_rels) - set(new_rels)) - set(relationship_renames)):
        classification = "breaking" if old_rels[name].required else "potentially_breaking"
        changes.append(
            _change(
                classification,
                "RELATIONSHIP_REMOVED",
                f"relationships.{name}",
                f"Relationship '{name}' was removed.",
            )
        )
    for name in sorted((set(new_rels) - set(old_rels)) - set(relationship_renames.values())):
        changes.append(
            _change(
                "non_breaking",
                "RELATIONSHIP_ADDED",
                f"relationships.{name}",
                f"Relationship '{name}' was added.",
            )
        )
    for name in sorted(set(old_rels) & set(new_rels)):
        if old_rels[name].from_ != new_rels[name].from_:
            changes.append(
                _change(
                    "breaking",
                    "RELATIONSHIP_SOURCE_CHANGED",
                    f"relationships.{name}.from",
                    f"Relationship '{name}' source changed.",
                )
            )
        if old_rels[name].to != new_rels[name].to:
            changes.append(
                _change(
                    "breaking",
                    "RELATIONSHIP_TARGET_CHANGED",
                    f"relationships.{name}.to",
                    f"Relationship '{name}' target changed.",
                )
            )
        if old_rels[name].cardinality != new_rels[name].cardinality:
            changes.append(
                _change(
                    "breaking",
                    "CARDINALITY_CHANGED",
                    f"relationships.{name}.cardinality",
                    f"Relationship '{name}' cardinality changed.",
                )
            )

    old_actions = {action.name: action for action in old.actions}
    new_actions = {action.name: action for action in new.actions}
    # Action aliases prevent renamed contracts from being reported as removed
    # and newly added, while preserving a migration warning for callers.
    action_renames = _alias_renames(
        set(old_actions) - set(new_actions),
        set(new_actions) - set(old_actions),
        {name: action.aliases for name, action in new_actions.items()},
    )
    for old_name, new_name in sorted(action_renames.items()):
        changes.append(
            _change(
                "potentially_breaking",
                "ACTION_RENAMED",
                f"actions.{new_name}.aliases",
                f"Action '{old_name}' appears to have been renamed to '{new_name}'.",
                "Keep the alias until callers migrate to the new action name.",
            )
        )
    for name in sorted((set(old_actions) - set(new_actions)) - set(action_renames)):
        changes.append(
            _change(
                "breaking", "ACTION_REMOVED", f"actions.{name}", f"Action '{name}' was removed."
            )
        )
    for name in sorted((set(new_actions) - set(old_actions)) - set(action_renames.values())):
        changes.append(
            _change(
                "non_breaking", "ACTION_ADDED", f"actions.{name}", f"Action '{name}' was added."
            )
        )
    for name in sorted(set(old_actions) & set(new_actions)):
        old_action = old_actions[name]
        new_action = new_actions[name]
        for input_name in sorted(set(old_action.inputs) - set(new_action.inputs)):
            changes.append(
                _change(
                    "breaking",
                    "ACTION_INPUT_REMOVED",
                    f"actions.{name}.inputs.{input_name}",
                    f"Action input '{input_name}' was removed from '{name}'.",
                )
            )
        for input_name in sorted(set(new_action.inputs) - set(old_action.inputs)):
            new_input = new_action.inputs[input_name]
            classification = (
                "breaking" if new_input.required and new_input.default is None else "non_breaking"
            )
            code = (
                "REQUIRED_ACTION_INPUT_ADDED"
                if classification == "breaking"
                else "OPTIONAL_ACTION_INPUT_ADDED"
            )
            changes.append(
                _change(
                    classification,
                    code,
                    f"actions.{name}.inputs.{input_name}",
                    f"Action input '{input_name}' was added to '{name}'.",
                )
            )
        for input_name in sorted(set(old_action.inputs) & set(new_action.inputs)):
            if old_action.inputs[input_name].type != new_action.inputs[input_name].type:
                changes.append(
                    _change(
                        "breaking",
                        "ACTION_INPUT_TYPE_CHANGED",
                        f"actions.{name}.inputs.{input_name}",
                        f"Action input '{input_name}' changed type.",
                    )
                )
        if old_action.output != new_action.output:
            changes.append(
                _change(
                    "potentially_breaking",
                    "ACTION_OUTPUT_CHANGED",
                    f"actions.{name}.output",
                    f"Action '{name}' output contract changed.",
                )
            )
        if set(new_action.permissions) - set(old_action.permissions):
            changes.append(
                _change(
                    "potentially_breaking",
                    "ACTION_PERMISSION_STRICTER",
                    f"actions.{name}.permissions",
                    f"Action '{name}' requires additional permissions.",
                )
            )
        if set(old_action.permissions) - set(new_action.permissions):
            changes.append(
                _change(
                    "non_breaking",
                    "ACTION_PERMISSION_RELAXED",
                    f"actions.{name}.permissions",
                    f"Action '{name}' requires fewer permissions.",
                )
            )
        if old_action.risk != new_action.risk:
            changes.append(
                _change(
                    "potentially_breaking",
                    "ACTION_RISK_CHANGED",
                    f"actions.{name}.risk",
                    f"Action '{name}' risk classification changed.",
                )
            )
        if old_action.review_required != new_action.review_required:
            classification = (
                "potentially_breaking" if new_action.review_required else "non_breaking"
            )
            changes.append(
                _change(
                    classification,
                    "ACTION_REVIEW_CHANGED",
                    f"actions.{name}.review_required",
                    f"Action '{name}' review requirement changed.",
                )
            )
        if old_action.preconditions != new_action.preconditions:
            changes.append(
                _change(
                    "potentially_breaking",
                    "ACTION_PRECONDITIONS_CHANGED",
                    f"actions.{name}.preconditions",
                    f"Action '{name}' preconditions changed.",
                )
            )

    old_permissions = set(old.permissions)
    new_permissions = set(new.permissions)
    referenced_old = {perm for action in old.actions for perm in action.permissions}
    for permission in sorted(old_permissions - new_permissions):
        classification = "breaking" if permission in referenced_old else "potentially_breaking"
        changes.append(
            _change(
                classification,
                "PERMISSION_REMOVED",
                f"permissions.{permission}",
                f"Permission '{permission}' was removed.",
            )
        )
    for permission in sorted(new_permissions - old_permissions):
        changes.append(
            _change(
                "non_breaking",
                "PERMISSION_ADDED",
                f"permissions.{permission}",
                f"Permission '{permission}' was added.",
            )
        )
    if old.ontology.description != new.ontology.description or old.metadata != new.metadata:
        changes.append(
            _change("informational", "METADATA_CHANGED", "ontology", "Ontology metadata changed.")
        )
    return DiffResult(
        changes=tuple(sorted(changes, key=lambda item: (item.classification, item.code, item.path)))
    )


def diff_text(result: DiffResult) -> str:
    """Return human-readable deterministic diff output."""

    lines = [
        "Ontology diff",
        f"Breaking: {result.breaking_count}",
        f"Potentially breaking: {result.potentially_breaking_count}",
        f"Non-breaking: {result.non_breaking_count}",
        f"Informational: {result.informational_count}",
        "",
    ]
    for change in result.changes:
        lines.append(f"[{change.classification}] {change.code} {change.path}: {change.message}")
    return "\n".join(lines).rstrip() + "\n"
