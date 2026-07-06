"""Validation result models."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["error", "warning", "info"]


class ValidationIssue(BaseModel):
    """A stable machine-readable validation issue."""

    model_config = ConfigDict(frozen=True)

    severity: Severity
    code: str
    message: str
    path: str
    suggestion: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """A collection of validation issues."""

    model_config = ConfigDict(frozen=True)

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        """Return error issues."""

        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        """Return warning issues."""

        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def infos(self) -> tuple[ValidationIssue, ...]:
        """Return informational issues."""

        return tuple(issue for issue in self.issues if issue.severity == "info")

    @property
    def ok(self) -> bool:
        """Whether the report has no errors."""

        return not self.errors

    def to_dict(self) -> dict[str, object]:
        """Serialize the report deterministically."""

        return {
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [issue.model_dump(exclude_none=True) for issue in self.issues],
        }
