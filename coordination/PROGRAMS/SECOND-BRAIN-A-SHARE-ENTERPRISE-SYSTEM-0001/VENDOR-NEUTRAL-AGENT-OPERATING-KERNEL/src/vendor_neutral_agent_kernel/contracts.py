"""Immutable public contracts for the vendor-neutral candidate kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _nonempty(name: str, value: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(name + "_REQUIRED")


def _ratio(name: str, value: float) -> None:
    if type(value) not in (int, float) or type(value) is bool or not 0.0 <= float(value) <= 1.0:
        raise ValueError(name + "_OUT_OF_RANGE")


def _unique(name: str, values: tuple[str, ...]) -> None:
    if type(values) is not tuple or any(type(item) is not str or not item for item in values):
        raise ValueError(name + "_INVALID")
    if len(set(values)) != len(values):
        raise ValueError(name + "_DUPLICATE")


class EpistemicLane(str, Enum):
    USER_ASSERTED = "USER_ASSERTED"
    USER_ADOPTED = "USER_ADOPTED"
    TOOL_OBSERVED = "TOOL_OBSERVED"
    INFERRED = "INFERRED"
    HYPOTHESIS = "HYPOTHESIS"
    DECISION = "DECISION"
    OUTCOME = "OUTCOME"
    UNKNOWN = "UNKNOWN"


class QualityStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    DISPUTED = "DISPUTED"
    STALE = "STALE"
    RETRACTED = "RETRACTED"
    UNKNOWN = "UNKNOWN"


class SideEffectClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    REVERSIBLE_LOCAL = "REVERSIBLE_LOCAL"
    EXTERNAL_REVERSIBLE = "EXTERNAL_REVERSIBLE"
    IRREVERSIBLE_OR_PRODUCTION = "IRREVERSIBLE_OR_PRODUCTION"


class CompletionStatus(str, Enum):
    SUCCESS_CLEAN = "SUCCESS_CLEAN"
    SUCCESS_WITH_FINDINGS = "SUCCESS_WITH_FINDINGS"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


class CapabilityAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ContractMeta:
    schema_version: str
    object_id: str
    run_id: str
    trace_id: str
    created_at: str
    source_refs: tuple[str, ...] = ()
    epistemic_status: EpistemicLane = EpistemicLane.UNKNOWN
    authority_class: str = "CANDIDATE_ONLY"
    quality_status: QualityStatus = QualityStatus.CANDIDATE
    content_hash: str = ""
    supersedes: str | None = None
    rollback_ref: str | None = None
    extensions: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        for name in ("schema_version", "object_id", "run_id", "trace_id", "created_at", "authority_class"):
            _nonempty(name, getattr(self, name))
        _unique("SOURCE_REFS", self.source_refs)
        if self.content_hash and (len(self.content_hash) != 64 or any(char not in "0123456789abcdef" for char in self.content_hash)):
            raise ValueError("CONTENT_HASH_INVALID")


@dataclass(frozen=True)
class AuthorityResolution:
    meta: ContractMeta
    effective_task_id: str
    agent_id: str
    allowed_paths: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    approval_requirements: tuple[str, ...]
    verified_approval_actions: tuple[str, ...]
    conflicts: tuple[str, ...]
    resolution_evidence: tuple[str, ...]
    resolution_status: str
    authority_hash: str

    def __post_init__(self) -> None:
        _nonempty("EFFECTIVE_TASK_ID", self.effective_task_id)
        _nonempty("AGENT_ID", self.agent_id)
        for field_name in (
            "allowed_paths",
            "allowed_actions",
            "forbidden_actions",
            "approval_requirements",
            "verified_approval_actions",
            "conflicts",
            "resolution_evidence",
        ):
            _unique(field_name.upper(), getattr(self, field_name))
        if set(self.allowed_actions) & set(self.forbidden_actions):
            raise ValueError("AUTHORITY_ACTION_CONTRADICTION")
        if not set(self.verified_approval_actions) <= set(self.approval_requirements):
            raise ValueError("VERIFIED_APPROVAL_NOT_REQUIRED")
        _nonempty("RESOLUTION_STATUS", self.resolution_status)
        _nonempty("AUTHORITY_HASH", self.authority_hash)


@dataclass(frozen=True)
class TaskIntent:
    meta: ContractMeta
    objective: str
    explicit_requirements: tuple[str, ...]
    success_criteria: tuple[str, ...]
    non_goals: tuple[str, ...]
    unknowns: tuple[str, ...]
    reversibility: str
    side_effect_class: SideEffectClass
    evidence_budget: int
    time_budget_seconds: int | None
    autonomy_boundary: tuple[str, ...]

    def __post_init__(self) -> None:
        _nonempty("OBJECTIVE", self.objective)
        _nonempty("REVERSIBILITY", self.reversibility)
        for field_name in (
            "explicit_requirements",
            "success_criteria",
            "non_goals",
            "unknowns",
            "autonomy_boundary",
        ):
            _unique(field_name.upper(), getattr(self, field_name))
        if self.evidence_budget < 0:
            raise ValueError("EVIDENCE_BUDGET_NEGATIVE")
        if self.time_budget_seconds is not None and self.time_budget_seconds <= 0:
            raise ValueError("TIME_BUDGET_INVALID")


@dataclass(frozen=True)
class EpistemicClaim:
    meta: ContractMeta
    canonical_statement: str
    provenance_lane: EpistemicLane
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    alternative_explanations: tuple[str, ...]
    confidence: float
    confidence_basis: str
    freshness: str
    invalidation_conditions: tuple[str, ...]
    review_after: str | None = None

    def __post_init__(self) -> None:
        _nonempty("CANONICAL_STATEMENT", self.canonical_statement)
        _ratio("CONFIDENCE", self.confidence)
        _nonempty("CONFIDENCE_BASIS", self.confidence_basis)
        _nonempty("FRESHNESS", self.freshness)
        for field_name in (
            "supporting_evidence",
            "opposing_evidence",
            "alternative_explanations",
            "invalidation_conditions",
        ):
            _unique(field_name.upper(), getattr(self, field_name))
        if self.provenance_lane in (EpistemicLane.INFERRED, EpistemicLane.HYPOTHESIS) and not self.supporting_evidence:
            raise ValueError("INFERENCE_REQUIRES_SUPPORTING_EVIDENCE")
        if self.provenance_lane is EpistemicLane.UNKNOWN and self.confidence != 0:
            raise ValueError("UNKNOWN_CONFIDENCE_MUST_BE_ZERO")


@dataclass(frozen=True)
class MemoryWriteProposal:
    meta: ContractMeta
    candidate_claims: tuple[EpistemicClaim, ...]
    destination_scope: str
    source_provenance: tuple[str, ...]
    validation_status: str
    authority_write: bool
    idempotency_key: str

    def __post_init__(self) -> None:
        if not self.candidate_claims:
            raise ValueError("MEMORY_PROPOSAL_REQUIRES_CLAIMS")
        _nonempty("DESTINATION_SCOPE", self.destination_scope)
        _unique("SOURCE_PROVENANCE", self.source_provenance)
        _nonempty("VALIDATION_STATUS", self.validation_status)
        _nonempty("IDEMPOTENCY_KEY", self.idempotency_key)
        if self.authority_write is not False:
            raise ValueError("MEMORY_PROPOSAL_CANNOT_WRITE_AUTHORITY")


@dataclass(frozen=True)
class CapabilityDescriptor:
    meta: ContractMeta
    provider_id: str
    provider_display_name: str
    capability_id: str
    semantics: tuple[str, ...]
    field_semantics_version: str
    source_quality: float
    authority_fit: float
    freshness_ms: int | None
    reliability: float
    latency_ms: int | None
    quota_remaining: int | None
    cost_units: float
    side_effect_class: SideEffectClass
    availability: CapabilityAvailability
    failure_modes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("provider_id", "provider_display_name", "capability_id", "field_semantics_version"):
            _nonempty(name, getattr(self, name))
        _unique("SEMANTICS", self.semantics)
        _unique("FAILURE_MODES", self.failure_modes)
        _ratio("SOURCE_QUALITY", self.source_quality)
        _ratio("AUTHORITY_FIT", self.authority_fit)
        _ratio("RELIABILITY", self.reliability)
        if self.freshness_ms is not None and self.freshness_ms < 0:
            raise ValueError("FRESHNESS_NEGATIVE")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("LATENCY_NEGATIVE")
        if self.quota_remaining is not None and self.quota_remaining < 0:
            raise ValueError("QUOTA_NEGATIVE")
        if self.cost_units < 0:
            raise ValueError("COST_NEGATIVE")


@dataclass(frozen=True)
class RouteCandidate:
    provider_id: str
    capability_id: str
    accepted: bool
    score: float
    components: tuple[tuple[str, float], ...]
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ToolRouteDecision:
    meta: ContractMeta
    requested_capability: str
    required_semantics: tuple[str, ...]
    candidates: tuple[RouteCandidate, ...]
    selected_provider_id: str | None
    selected_capability_id: str | None
    fallback_order: tuple[str, ...]
    decision_hash: str

    def __post_init__(self) -> None:
        _nonempty("REQUESTED_CAPABILITY", self.requested_capability)
        _unique("REQUIRED_SEMANTICS", self.required_semantics)
        _unique("FALLBACK_ORDER", self.fallback_order)
        _nonempty("DECISION_HASH", self.decision_hash)
        if (self.selected_provider_id is None) != (self.selected_capability_id is None):
            raise ValueError("ROUTE_SELECTION_PARTIAL")


@dataclass(frozen=True)
class SideEffectRecord:
    effect_id: str
    side_effect_class: SideEffectClass
    idempotency_key: str
    external_anchor: str | None
    status: str


@dataclass(frozen=True)
class ExecutionCheckpoint:
    meta: ContractMeta
    intent_hash: str
    context_hash: str
    authority_hash: str
    completed_steps: tuple[str, ...]
    remaining_steps: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    side_effect_ledger: tuple[SideEffectRecord, ...]
    test_state: tuple[str, ...]
    resume_instructions: tuple[str, ...]
    external_anchors: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("INTENT_HASH", "CONTEXT_HASH", "AUTHORITY_HASH"):
            _nonempty(name, getattr(self, name.lower()))
        for name in ("COMPLETED_STEPS", "REMAINING_STEPS", "ARTIFACT_REFS", "TEST_STATE", "RESUME_INSTRUCTIONS", "EXTERNAL_ANCHORS"):
            _unique(name, getattr(self, name.lower()))
        keys = tuple(item.idempotency_key for item in self.side_effect_ledger)
        if len(set(keys)) != len(keys):
            raise ValueError("DUPLICATE_SIDE_EFFECT_IDEMPOTENCY_KEY")


@dataclass(frozen=True)
class RequirementEvidence:
    requirement_id: str
    evidence_refs: tuple[str, ...]
    disposition: str
    scope: str

    def __post_init__(self) -> None:
        _nonempty("REQUIREMENT_ID", self.requirement_id)
        _unique("EVIDENCE_REFS", self.evidence_refs)
        _nonempty("DISPOSITION", self.disposition)
        _nonempty("SCOPE", self.scope)


@dataclass(frozen=True)
class CompletionReceipt:
    meta: ContractMeta
    requirement_evidence: tuple[RequirementEvidence, ...]
    changed_files: tuple[str, ...]
    tests: tuple[str, ...]
    external_anchors: tuple[str, ...]
    unknowns: tuple[str, ...]
    findings: tuple[str, ...]
    rollback: tuple[str, ...]
    completion_status: CompletionStatus

    def __post_init__(self) -> None:
        ids = tuple(item.requirement_id for item in self.requirement_evidence)
        if len(set(ids)) != len(ids):
            raise ValueError("DUPLICATE_REQUIREMENT_EVIDENCE")
        for name in ("CHANGED_FILES", "TESTS", "EXTERNAL_ANCHORS", "UNKNOWNS", "FINDINGS", "ROLLBACK"):
            _unique(name, getattr(self, name.lower()))


@dataclass(frozen=True)
class AgentHandoff:
    meta: ContractMeta
    source_agent: str
    target_agent: str
    reviewer: str
    task_id: str
    owned_paths: tuple[str, ...]
    base: str
    parent: str
    tree: str
    head: str
    completed: tuple[str, ...]
    remaining: tuple[str, ...]
    tests: tuple[str, ...]
    unknowns: tuple[str, ...]
    rollback: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("source_agent", "target_agent", "reviewer", "task_id", "base", "parent", "tree", "head"):
            _nonempty(name, getattr(self, name))
        for name in ("OWNED_PATHS", "COMPLETED", "REMAINING", "TESTS", "UNKNOWNS", "ROLLBACK"):
            _unique(name, getattr(self, name.lower()))


@dataclass(frozen=True)
class ModelBehaviorProfile:
    meta: ContractMeta
    model_family: str
    model_version: str
    evaluated_at: str
    evaluation_refs: tuple[str, ...]
    task_strengths: tuple[str, ...]
    known_failure_modes: tuple[str, ...]
    verbosity_profile: str
    tool_use_profile: str
    verification_profile: str
    delegation_profile: str
    structured_output_profile: str
    effective_from: str
    review_after: str
    authority_overrides: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        for name in (
            "model_family", "model_version", "evaluated_at", "verbosity_profile",
            "tool_use_profile", "verification_profile", "delegation_profile",
            "structured_output_profile", "effective_from", "review_after",
        ):
            _nonempty(name, getattr(self, name))
        for name in ("EVALUATION_REFS", "TASK_STRENGTHS", "KNOWN_FAILURE_MODES", "AUTHORITY_OVERRIDES"):
            _unique(name, getattr(self, name.lower()))
        if self.authority_overrides:
            raise ValueError("MODEL_PROFILE_CANNOT_OVERRIDE_AUTHORITY")
