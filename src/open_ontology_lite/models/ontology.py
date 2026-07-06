"""Core ontology data models."""

from collections.abc import Iterable
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PropertyType = Literal[
    "string",
    "integer",
    "number",
    "decimal",
    "boolean",
    "date",
    "datetime",
    "uuid",
    "object",
    "array",
    "reference",
]
Cardinality = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class StrictModel(BaseModel):
    """Base model that rejects unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


def _tuple_or_empty(value: object) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(value)
    return (value,)


class OntologyMetadata(StrictModel):
    """Ontology-level metadata."""

    id: str
    name: str
    version: str
    namespace: str
    description: str = ""
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, value: object) -> object:
        return _tuple_or_empty(value)


class PropertyDef(StrictModel):
    """A typed property, action input, or output definition."""

    type: PropertyType
    aliases: tuple[str, ...] = ()
    required: bool = False
    nullable: bool = False
    description: str = ""
    default: Any = None
    enum: tuple[Any, ...] | None = None
    pattern: str | None = None
    minimum: Decimal | int | float | None = None
    maximum: Decimal | int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    items: PropertyType | None = None
    target: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("enum", mode="before")
    @classmethod
    def _enum(cls, value: object) -> object:
        return None if value is None else _tuple_or_empty(value)

    @field_validator("aliases", mode="before")
    @classmethod
    def _aliases(cls, value: object) -> object:
        return _tuple_or_empty(value)


class EntityDef(StrictModel):
    """An ontology entity."""

    id: str | None = None
    name: str | None = None
    aliases: tuple[str, ...] = ()
    description: str = ""
    properties: dict[str, PropertyDef] = Field(default_factory=dict)
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, value: object) -> object:
        return _tuple_or_empty(value)

    @field_validator("aliases", mode="before")
    @classmethod
    def _aliases(cls, value: object) -> object:
        return _tuple_or_empty(value)


class RelationshipDef(StrictModel):
    """A relationship between two entities."""

    name: str
    aliases: tuple[str, ...] = ()
    from_: str = Field(alias="from")
    to: str
    cardinality: Cardinality
    description: str = ""
    inverse: str | None = None
    required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("aliases", mode="before")
    @classmethod
    def _aliases(cls, value: object) -> object:
        return _tuple_or_empty(value)


class ActionDef(StrictModel):
    """A declarative action contract."""

    name: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    subject: str
    inputs: dict[str, PropertyDef] = Field(default_factory=dict)
    output: PropertyDef | None = None
    permissions: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    effects: str = ""
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("aliases", "permissions", "preconditions", "tags", mode="before")
    @classmethod
    def _tuple(cls, value: object) -> object:
        return _tuple_or_empty(value)


class PermissionDef(StrictModel):
    """A named permission declaration."""

    description: str = ""
    risk: RiskLevel = "low"
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, value: object) -> object:
        return _tuple_or_empty(value)


class Ontology(StrictModel):
    """A normalized internal ontology model."""

    schema_version: str
    ontology: OntologyMetadata
    entities: dict[str, EntityDef]
    relationships: tuple[RelationshipDef, ...] = ()
    actions: tuple[ActionDef, ...] = ()
    permissions: dict[str, PermissionDef] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("relationships", "actions", mode="before")
    @classmethod
    def _as_tuple(cls, value: object) -> object:
        return _tuple_or_empty(value)

    @model_validator(mode="after")
    def _inject_entity_ids(self) -> "Ontology":
        enriched = {
            key: value.model_copy(update={"id": value.id or key, "name": value.name or key})
            for key, value in self.entities.items()
        }
        if enriched != self.entities:
            return self.model_copy(update={"entities": enriched})
        return self
