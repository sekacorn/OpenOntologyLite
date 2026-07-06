"""Diff result models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

ChangeClass = Literal["breaking", "potentially_breaking", "non_breaking", "informational"]


class DiffChange(BaseModel):
    """One classified ontology change."""

    model_config = ConfigDict(frozen=True)

    classification: ChangeClass
    code: str
    path: str
    message: str


class DiffResult(BaseModel):
    """Ontology diff result."""

    model_config = ConfigDict(frozen=True)

    changes: tuple[DiffChange, ...]

    @property
    def breaking_count(self) -> int:
        """Count breaking changes."""

        return sum(1 for change in self.changes if change.classification == "breaking")

    @property
    def potentially_breaking_count(self) -> int:
        """Count potentially breaking changes."""

        return sum(1 for change in self.changes if change.classification == "potentially_breaking")

    @property
    def non_breaking_count(self) -> int:
        """Count non-breaking changes."""

        return sum(1 for change in self.changes if change.classification == "non_breaking")

    @property
    def informational_count(self) -> int:
        """Count informational changes."""

        return sum(1 for change in self.changes if change.classification == "informational")

    def to_dict(self) -> dict[str, object]:
        """Serialize with summary counts."""

        return {
            "summary": {
                "breaking": self.breaking_count,
                "potentially_breaking": self.potentially_breaking_count,
                "non_breaking": self.non_breaking_count,
                "informational": self.informational_count,
            },
            "changes": [change.model_dump() for change in self.changes],
        }
