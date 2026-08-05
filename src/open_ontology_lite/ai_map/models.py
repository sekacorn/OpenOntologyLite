"""Typed models for portable AI System Maps."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

ROUTE_NAMES = (
    "candidate_model",
    "baseline_model",
    "human_review",
    "blocked_or_escalate",
)
RISK_LEVELS = ("low", "medium", "high", "regulated", "unknown")
SENSITIVITY_LEVELS = ("public", "internal", "confidential", "restricted", "unknown")
ESCALATION_NAMES = (
    "human_review",
    "security_review",
    "legal_review",
    "compliance_review",
    "do_not_answer",
    "baseline_model_only",
)


def _tuple_or_empty(value: Any) -> Any:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(value)
    return value


ShortString = Annotated[str, Field(max_length=160)]
LongString = Annotated[str, Field(max_length=2_000)]
StringTuple = Annotated[tuple[ShortString, ...], BeforeValidator(_tuple_or_empty)]
TextTuple = Annotated[tuple[LongString, ...], BeforeValidator(_tuple_or_empty)]


class AIStrictModel(BaseModel):
    """Base model with deterministic, immutable behavior."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


class AISystemMetadata(AIStrictModel):
    """Identity and operational context for an AI-enabled system."""

    name: str = Field(default="", max_length=160)
    purpose: str = Field(default="", max_length=2_000)
    owner_label: str | None = Field(default=None, max_length=160)
    risk_profile: str = Field(default="unknown", max_length=40)
    environment: str = Field(default="unspecified", max_length=80)
    notes: str | None = Field(default=None, max_length=2_000)


class AIEntity(AIStrictModel):
    """A business entity read or produced by AI tasks."""

    name: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=2_000)
    sensitivity: str = Field(default="unknown", max_length=40)
    fields: StringTuple = Field(default=(), max_length=100)
    notes: str | None = Field(default=None, max_length=2_000)


class AITask(AIStrictModel):
    """An AI workload with routing and control requirements."""

    name: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=2_000)
    category: str = Field(default="general", max_length=120)
    risk_level: str = Field(default="unknown", max_length=40)
    customer_facing: bool = False
    allowed_routes: StringTuple = Field(default=(), max_length=20)
    human_review_required: bool = False
    audit_required: bool = True
    cost_tracking_required: bool = True
    escalation: StringTuple = Field(default=(), max_length=20)
    related_entities: StringTuple = Field(default=(), max_length=100)
    policy_tags: StringTuple = Field(default=(), max_length=100)
    expected_audit_events: StringTuple = Field(default=(), max_length=100)
    expected_metrics: StringTuple = Field(default=(), max_length=100)
    data_sources: StringTuple = Field(default=(), max_length=100)
    retrieval_boundaries: StringTuple = Field(default=(), max_length=100)
    models: StringTuple = Field(default=(), max_length=50)
    fallback_models: StringTuple = Field(default=(), max_length=50)
    agent_roles: StringTuple = Field(default=(), max_length=100)
    tool_access: StringTuple = Field(default=(), max_length=100)
    human_review_points: StringTuple = Field(default=(), max_length=50)
    policy_bundle_references: StringTuple = Field(default=(), max_length=100)
    known_failure_modes: TextTuple = Field(default=(), max_length=100)
    data_retention: str | None = Field(default=None, max_length=500)
    deployment_restrictions: TextTuple = Field(default=(), max_length=100)
    geographic_restrictions: StringTuple = Field(default=(), max_length=100)
    integration_contract_references: StringTuple = Field(default=(), max_length=100)
    ontology_entities: StringTuple = Field(default=(), max_length=100)
    ontology_actions: StringTuple = Field(default=(), max_length=100)
    ontology_permissions: StringTuple = Field(default=(), max_length=100)
    data_handling_expectations: TextTuple = Field(default=(), max_length=100)
    escalation_required: bool = False
    provenance: dict[ShortString, LongString] = Field(default_factory=dict, max_length=100)
    candidate_route_justification: str | None = Field(default=None, max_length=2_000)
    notes: str | None = Field(default=None, max_length=2_000)


class ModelRoute(AIStrictModel):
    """A declared model-routing destination."""

    name: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=1_000)


class EscalationPath(AIStrictModel):
    """A declared human or control escalation path."""

    name: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=1_000)


class AIIntegration(AIStrictModel):
    """The portable meaning assigned to an external integration."""

    tool: str = Field(default="", max_length=120)
    meaning: str = Field(default="", max_length=2_000)
    mode: str = Field(default="integration_pattern", max_length=80)


def _default_model_routes() -> tuple[ModelRoute, ...]:
    return (
        ModelRoute(
            name="candidate_model",
            description="Evaluate a candidate model under the task's declared controls.",
        ),
        ModelRoute(
            name="baseline_model",
            description="Use the established baseline model path.",
        ),
        ModelRoute(
            name="human_review",
            description="Route the task to an authorized human reviewer.",
        ),
        ModelRoute(
            name="blocked_or_escalate",
            description="Block automation or use a declared escalation path.",
        ),
    )


def _default_escalation_paths() -> tuple[EscalationPath, ...]:
    return (
        EscalationPath(name="human_review", description="Authorized human review."),
        EscalationPath(name="security_review", description="Security response review."),
        EscalationPath(name="legal_review", description="Qualified legal review."),
        EscalationPath(name="compliance_review", description="Compliance review."),
        EscalationPath(name="do_not_answer", description="Do not generate an answer."),
        EscalationPath(
            name="baseline_model_only",
            description="Keep the task on the established baseline path.",
        ),
    )


def _default_limitations() -> tuple[str, ...]:
    return (
        "This map provides documentation and validation support, not compliance certification.",
        "This map does not prove that a workflow is safe.",
        "This map does not replace human review for high-risk uses.",
        "This map does not prove legal, regulatory, safety, or security compliance.",
        "This map does not guarantee model behavior.",
        "This map does not enforce policy unless connected to enforcement systems.",
        "Integration entries describe portable meaning, not verified live integrations.",
    )


class AISystemMap(AIStrictModel):
    """A portable map of AI workloads, routes, controls, and integrations."""

    schema_version: str = Field(default="1.0", max_length=20)
    system: AISystemMetadata = Field(default_factory=AISystemMetadata)
    entities: tuple[AIEntity, ...] = Field(default=(), max_length=1_000)
    tasks: tuple[AITask, ...] = Field(default=(), max_length=5_000)
    model_routes: tuple[ModelRoute, ...] = Field(
        default_factory=_default_model_routes, max_length=20
    )
    escalation_paths: tuple[EscalationPath, ...] = Field(
        default_factory=_default_escalation_paths, max_length=50
    )
    integrations: tuple[AIIntegration, ...] = Field(default=(), max_length=100)
    limitations: TextTuple = Field(default_factory=_default_limitations, max_length=100)
