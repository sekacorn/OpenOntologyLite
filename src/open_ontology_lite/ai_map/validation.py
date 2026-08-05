"""Semantic validation for AI System Maps."""

from __future__ import annotations

import re

from open_ontology_lite.ai_map.models import (
    ESCALATION_NAMES,
    RISK_LEVELS,
    ROUTE_NAMES,
    SENSITIVITY_LEVELS,
    AISystemMap,
)
from open_ontology_lite.models import Ontology
from open_ontology_lite.models.validation import ValidationIssue

_SENSITIVE_CATEGORIES = {
    "financial",
    "legal",
    "medical",
    "regulated",
    "safety",
    "security",
}
MAX_VALIDATION_ISSUES = 1_000


class AISystemMapValidationResult:
    """Stable validation result for an AI System Map."""

    def __init__(self, issues: tuple[ValidationIssue, ...] = ()) -> None:
        self.issues = issues

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def ok(self) -> bool:
        return self.valid

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [issue.model_dump(exclude_none=True) for issue in self.issues],
        }


class _IssueCollector:
    def __init__(self) -> None:
        self._issues: list[ValidationIssue] = []
        self._truncated = False

    def append(self, issue: ValidationIssue) -> None:
        if len(self._issues) < MAX_VALIDATION_ISSUES:
            self._issues.append(issue)
        else:
            self._truncated = True

    def to_tuple(self) -> tuple[ValidationIssue, ...]:
        if not self._truncated:
            return tuple(self._issues)
        limit_issue = _issue(
            "error",
            "VALIDATION_ISSUE_LIMIT",
            f"Validation produced more than {MAX_VALIDATION_ISSUES} issues.",
            "<root>",
            "Resolve the reported issues and validate again.",
        )
        return (*self._issues, limit_issue)


def _issue(
    severity: str,
    code: str,
    message: str,
    path: str,
    suggestion: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
        path=path,
        suggestion=suggestion,
    )


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        normalized = value.casefold()
        if normalized in seen:
            duplicates.add(value)
        seen.add(normalized)
    return duplicates


def _category_tokens(category: str) -> set[str]:
    return set(re.findall(r"[a-z]+", category.casefold()))


def validate_ai_system_map(
    ai_map: AISystemMap, ontology: Ontology | None = None
) -> AISystemMapValidationResult:
    """Validate references, routing controls, and reporting expectations."""

    issues = _IssueCollector()
    if ai_map.schema_version != "1.0":
        issues.append(
            _issue(
                "error",
                "UNSUPPORTED_SCHEMA_VERSION",
                f"Unsupported AI System Map schema version: {ai_map.schema_version}",
                "schema_version",
                "Use schema_version 1.0.",
            )
        )
    if not ai_map.system.name:
        issues.append(
            _issue(
                "error",
                "SYSTEM_NAME_REQUIRED",
                "The system name is required.",
                "system.name",
            )
        )
    if ai_map.system.risk_profile not in RISK_LEVELS:
        issues.append(
            _issue(
                "error",
                "INVALID_SYSTEM_RISK",
                f"Unknown system risk profile: {ai_map.system.risk_profile}",
                "system.risk_profile",
                f"Use one of: {', '.join(RISK_LEVELS)}.",
            )
        )
    elif ai_map.system.risk_profile == "unknown":
        issues.append(
            _issue(
                "warning",
                "UNKNOWN_SYSTEM_RISK",
                "The system risk profile is unknown.",
                "system.risk_profile",
                "Assess and assign a risk level before deployment.",
            )
        )

    entity_names = [entity.name for entity in ai_map.entities if entity.name]
    known_entities = set(entity_names)
    for duplicate in sorted(_duplicates(entity_names)):
        issues.append(
            _issue(
                "error",
                "DUPLICATE_ENTITY",
                f"Entity name is duplicated: {duplicate}",
                "entities",
            )
        )
    for index, entity in enumerate(ai_map.entities):
        path = f"entities[{index}]"
        if not entity.name:
            issues.append(
                _issue("error", "ENTITY_NAME_REQUIRED", "Entity name is required.", f"{path}.name")
            )
        if entity.sensitivity not in SENSITIVITY_LEVELS:
            issues.append(
                _issue(
                    "error",
                    "INVALID_ENTITY_SENSITIVITY",
                    f"Unknown sensitivity level: {entity.sensitivity}",
                    f"{path}.sensitivity",
                    f"Use one of: {', '.join(SENSITIVITY_LEVELS)}.",
                )
            )

    task_names = [task.name for task in ai_map.tasks if task.name]
    for duplicate in sorted(_duplicates(task_names)):
        issues.append(
            _issue(
                "error",
                "DUPLICATE_TASK",
                f"Task name is duplicated: {duplicate}",
                "tasks",
            )
        )

    declared_routes = {route.name for route in ai_map.model_routes}
    for duplicate in sorted(_duplicates([route.name for route in ai_map.model_routes])):
        issues.append(
            _issue(
                "error",
                "DUPLICATE_MODEL_ROUTE",
                f"Model route is declared more than once: {duplicate}",
                "model_routes",
            )
        )
    for index, route in enumerate(ai_map.model_routes):
        if route.name not in ROUTE_NAMES:
            issues.append(
                _issue(
                    "error",
                    "INVALID_MODEL_ROUTE",
                    f"Unknown model route: {route.name}",
                    f"model_routes[{index}].name",
                    f"Use one of: {', '.join(ROUTE_NAMES)}.",
                )
            )
    for route_name in ROUTE_NAMES:
        if route_name not in declared_routes:
            issues.append(
                _issue(
                    "error",
                    "MODEL_ROUTE_NOT_DECLARED",
                    f"Required model route is not declared: {route_name}",
                    "model_routes",
                )
            )

    declared_escalations = {path.name for path in ai_map.escalation_paths}
    for duplicate in sorted(_duplicates([path.name for path in ai_map.escalation_paths])):
        issues.append(
            _issue(
                "error",
                "DUPLICATE_ESCALATION_PATH",
                f"Escalation path is declared more than once: {duplicate}",
                "escalation_paths",
            )
        )
    for index, escalation in enumerate(ai_map.escalation_paths):
        if escalation.name not in ESCALATION_NAMES:
            issues.append(
                _issue(
                    "error",
                    "INVALID_ESCALATION_PATH",
                    f"Unknown escalation path: {escalation.name}",
                    f"escalation_paths[{index}].name",
                    f"Use one of: {', '.join(ESCALATION_NAMES)}.",
                )
            )

    for index, task in enumerate(ai_map.tasks):
        path = f"tasks[{index}]"
        if not task.name:
            issues.append(
                _issue("error", "TASK_NAME_REQUIRED", "Task name is required.", f"{path}.name")
            )
        if task.risk_level not in RISK_LEVELS:
            issues.append(
                _issue(
                    "error",
                    "INVALID_TASK_RISK",
                    f"Unknown task risk level: {task.risk_level}",
                    f"{path}.risk_level",
                    f"Use one of: {', '.join(RISK_LEVELS)}.",
                )
            )
        elif task.risk_level == "unknown":
            issues.append(
                _issue(
                    "warning",
                    "UNKNOWN_TASK_RISK",
                    "The task risk level is unknown.",
                    f"{path}.risk_level",
                    "Assess and assign a risk level before enabling model routes.",
                )
            )
        if not task.allowed_routes:
            issues.append(
                _issue(
                    "error",
                    "ROUTE_REQUIRED",
                    "At least one allowed model route is required.",
                    f"{path}.allowed_routes",
                )
            )
        for route_name in task.allowed_routes:
            if route_name not in ROUTE_NAMES:
                issues.append(
                    _issue(
                        "error",
                        "INVALID_TASK_ROUTE",
                        f"Unknown model route: {route_name}",
                        f"{path}.allowed_routes",
                        f"Use one of: {', '.join(ROUTE_NAMES)}.",
                    )
                )
            elif route_name not in declared_routes:
                issues.append(
                    _issue(
                        "error",
                        "UNDECLARED_TASK_ROUTE",
                        f"Task uses an undeclared model route: {route_name}",
                        f"{path}.allowed_routes",
                    )
                )
        for entity_name in task.related_entities:
            if entity_name not in known_entities:
                issues.append(
                    _issue(
                        "error",
                        "UNKNOWN_RELATED_ENTITY",
                        f"Task references an unknown entity: {entity_name}",
                        f"{path}.related_entities",
                    )
                )
        for escalation_name in task.escalation:
            if escalation_name not in ESCALATION_NAMES:
                issues.append(
                    _issue(
                        "error",
                        "INVALID_TASK_ESCALATION",
                        f"Unknown escalation path: {escalation_name}",
                        f"{path}.escalation",
                    )
                )
            elif escalation_name not in declared_escalations:
                issues.append(
                    _issue(
                        "error",
                        "UNDECLARED_TASK_ESCALATION",
                        f"Task uses an undeclared escalation path: {escalation_name}",
                        f"{path}.escalation",
                    )
                )

        candidate_allowed = "candidate_model" in task.allowed_routes
        if task.risk_level in {"high", "regulated", "unknown"} and candidate_allowed:
            if not task.human_review_required and not task.candidate_route_justification:
                severity = "error" if task.risk_level == "regulated" else "warning"
                issues.append(
                    _issue(
                        severity,
                        "HIGH_RISK_CANDIDATE_ROUTE",
                        "A high-risk candidate route needs human review or explicit justification.",
                        f"{path}.allowed_routes",
                        "Require human review, remove candidate_model, or document the exception.",
                    )
                )
            elif not task.human_review_required:
                issues.append(
                    _issue(
                        "warning",
                        "CANDIDATE_ROUTE_EXCEPTION",
                        "A high-risk candidate route relies on a documented exception.",
                        f"{path}.candidate_route_justification",
                        "Review and approve the exception before deployment.",
                    )
                )

        sensitive = task.risk_level == "regulated" or bool(
            _category_tokens(task.category) & _SENSITIVE_CATEGORIES
        )
        controlled = (
            task.human_review_required
            or bool(task.escalation)
            or "blocked_or_escalate" in task.allowed_routes
        )
        if sensitive and not controlled:
            issues.append(
                _issue(
                    "error",
                    "SENSITIVE_TASK_CONTROL_REQUIRED",
                    "Sensitive tasks require human review, blocking, or an escalation path.",
                    path,
                )
            )
        if sensitive and not task.data_handling_expectations:
            issues.append(
                _issue(
                    "warning",
                    "SENSITIVE_DATA_HANDLING_REQUIRED",
                    "Sensitive tasks require declared data-handling expectations.",
                    f"{path}.data_handling_expectations",
                )
            )
        if task.human_review_required and not (
            task.human_review_points or task.escalation or "human_review" in task.allowed_routes
        ):
            issues.append(
                _issue(
                    "error",
                    "HUMAN_REVIEW_PATH_REQUIRED",
                    "Human review is required but no review point or review route is declared.",
                    f"{path}.human_review_points",
                )
            )
        if task.escalation_required and not task.escalation:
            issues.append(
                _issue(
                    "error",
                    "ESCALATION_ROUTE_REQUIRED",
                    "Escalation is required but no escalation route is declared.",
                    f"{path}.escalation",
                )
            )
        if task.audit_required and not task.expected_audit_events:
            issues.append(
                _issue(
                    "warning",
                    "AUDIT_EXPECTATION_REQUIRED",
                    "Audit is required but no expected audit events are listed.",
                    f"{path}.expected_audit_events",
                )
            )
        if task.cost_tracking_required and not task.expected_metrics:
            issues.append(
                _issue(
                    "warning",
                    "COST_EXPECTATION_REQUIRED",
                    "Cost tracking is required but no expected metrics are listed.",
                    f"{path}.expected_metrics",
                )
            )
        if "blocked_or_escalate" in task.allowed_routes and not task.escalation:
            issues.append(
                _issue(
                    "warning",
                    "BLOCKED_ROUTE_WITHOUT_ESCALATION",
                    "The blocked route has no declared escalation destination.",
                    f"{path}.escalation",
                )
            )
        if ontology is not None:
            ontology_entities = set(ontology.entities)
            ontology_actions = {action.name for action in ontology.actions}
            ontology_permissions = set(ontology.permissions)
            for entity_name in task.ontology_entities:
                if entity_name not in ontology_entities:
                    issues.append(
                        _issue(
                            "error",
                            "UNKNOWN_ONTOLOGY_ENTITY",
                            f"Task references an unknown ontology entity: {entity_name}",
                            f"{path}.ontology_entities",
                        )
                    )
            for action_name in task.ontology_actions:
                if action_name not in ontology_actions:
                    issues.append(
                        _issue(
                            "error",
                            "UNKNOWN_ONTOLOGY_ACTION",
                            f"Task references an unknown ontology action: {action_name}",
                            f"{path}.ontology_actions",
                        )
                    )
            for permission_name in task.ontology_permissions:
                if permission_name not in ontology_permissions:
                    issues.append(
                        _issue(
                            "error",
                            "UNKNOWN_ONTOLOGY_PERMISSION",
                            f"Task references an unknown ontology permission: {permission_name}",
                            f"{path}.ontology_permissions",
                        )
                    )

    return AISystemMapValidationResult(issues.to_tuple())
