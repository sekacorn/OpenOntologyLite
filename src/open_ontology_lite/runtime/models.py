"""Typed results for executable semantic-contract validation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from open_ontology_lite.models.validation import ValidationIssue

ContractStatus = Literal["satisfied", "unsatisfied", "indeterminate"]


class RuntimeResultModel(BaseModel):
    """Immutable base for deterministic runtime results."""

    model_config = ConfigDict(frozen=True)


class EntityValidationResult(RuntimeResultModel):
    """Result of validating one entity instance."""

    valid: bool
    entity_type: str
    issues: tuple[ValidationIssue, ...] = ()
    normalized_value: dict[str, Any] | None = None
    aliases_required: bool = False
    defaults_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible deterministic representation."""

        return {
            "valid": self.valid,
            "entity_type": self.entity_type,
            "aliases_required": self.aliases_required,
            "defaults_required": self.defaults_required,
            "normalized_value": _json_value(self.normalized_value),
            "issues": [issue.model_dump(exclude_none=True) for issue in self.issues],
        }


class ActionContractResult(RuntimeResultModel):
    """Non-enforcing semantic check of a proposed action invocation."""

    status: ContractStatus
    action: str
    issues: tuple[ValidationIssue, ...] = ()
    validated_inputs: dict[str, Any] | None = None
    validated_output: Any = None
    required_permissions: tuple[str, ...] = ()
    missing_permissions: tuple[str, ...] = ()
    resolved_preconditions: tuple[str, ...] = ()
    unresolved_preconditions: tuple[str, ...] = ()
    risk: str = "unknown"
    review_required: bool = False
    escalation_expectations: tuple[str, ...] = ()
    audit_required: bool = False
    expected_audit_events: tuple[str, ...] = ()
    evidence_paths: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        """Whether the semantic contract is fully satisfied."""

        return self.status == "satisfied"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible deterministic representation."""

        return {
            "status": self.status,
            "action": self.action,
            "validated_inputs": _json_value(self.validated_inputs),
            "validated_output": _json_value(self.validated_output),
            "required_permissions": list(self.required_permissions),
            "missing_permissions": list(self.missing_permissions),
            "resolved_preconditions": list(self.resolved_preconditions),
            "unresolved_preconditions": list(self.unresolved_preconditions),
            "risk": self.risk,
            "review_required": self.review_required,
            "escalation_expectations": list(self.escalation_expectations),
            "audit_required": self.audit_required,
            "expected_audit_events": list(self.expected_audit_events),
            "evidence_paths": list(self.evidence_paths),
            "issues": [issue.model_dump(exclude_none=True) for issue in self.issues],
        }


def _json_value(value: Any) -> Any:
    from decimal import Decimal

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value
