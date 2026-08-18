from __future__ import annotations

from _iagl_primitives import *
from _iagl_events import *

@dataclass(frozen=True)
class ReconciliationGrant:
    identity: str
    generation: int


@dataclass(frozen=True)
class RetrievalProviderObservation:
    observation_id: str
    provider_source: str
    repository: str
    exact_revision: str
    request_digest: str
    authority_scope_ref: str
    evidence_ref: str
    complete_empty: bool

    def validate(self) -> None:
        if self.provider_source != "SYNTHETIC_RETRIEVAL_PROVIDER" or not self.complete_empty:
            raise SupervisorError("RETRIEVAL_PROVIDER_OBSERVATION_UNTRUSTED")
        if not _nonempty((self.observation_id, self.repository, self.exact_revision, self.request_digest, self.authority_scope_ref, self.evidence_ref)):
            raise SupervisorError("RETRIEVAL_PROVIDER_OBSERVATION_INCOMPLETE")

    def observation_digest(self) -> str:
        return digest(asdict(self))


class SyntheticRetrievalProvider:
    def __init__(self, observations: Sequence[RetrievalProviderObservation] = ()):
        self._observations: dict[tuple[str, str, str, str], RetrievalProviderObservation] = {}
        for observation in observations:
            observation.validate()
            key = (observation.repository, observation.exact_revision, observation.request_digest, observation.authority_scope_ref)
            if key in self._observations:
                raise SupervisorError("DUPLICATE_RETRIEVAL_PROVIDER_OBSERVATION")
            self._observations[key] = observation

    def observe_complete_empty(self, repository: str, exact_revision: str, request_digest: str, authority_scope_ref: str) -> RetrievalProviderObservation | None:
        return self._observations.get((repository, exact_revision, request_digest, authority_scope_ref))


@dataclass(frozen=True)
class RetrievalCompletenessProof:
    repository: str
    exact_revision: str
    request_digest: str
    authority_scope_ref: str
    evidence_ref: str
    provider_observation_ref: str
    provider_observation_digest: str
    reconciliation_identity: str
    reconciliation_generation: int
    complete_empty: bool
    issuance_ref: str = ""

    def structurally_matches(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant, request_digest: str) -> bool:
        return bool(
            self.complete_empty
            and _nonempty((self.repository, self.exact_revision, self.request_digest, self.authority_scope_ref, self.evidence_ref, self.provider_observation_ref, self.provider_observation_digest, self.reconciliation_identity, self.issuance_ref))
            and self.repository == snapshot.repository and self.exact_revision == snapshot.exact_head
            and self.request_digest == request_digest and self.reconciliation_identity == grant.identity
            and self.reconciliation_generation == grant.generation
        )

    def proof_digest(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class ImprovementSlice:
    slice_id: str
    priority: Priority
    changed_paths: tuple[str, ...]
    source_signal_refs: tuple[str, ...]
    problem_signature: str
    goal: str
    materiality: str
    evidence_target: str
    allowed_tools: tuple[str, ...]
    allowed_data_classes: tuple[str, ...]
    risk_class: str
    time_budget_minutes: int
    compute_budget: int
    expected_artifact: str
    falsifier: str
    stop_conditions: tuple[str, ...]
    writeback_plan: str
    owner: str
    estimated_cost: int = 1
    evidence_value: int = 1
    action_kind: str = "SYNTHETIC_FIXED_ACTION"
    authority_metadata: Mapping[str, Any] | None = None

    def validate(self, snapshot: ReconciliationSnapshot) -> None:
        strings = (self.slice_id, self.problem_signature, self.goal, self.materiality, self.evidence_target, self.risk_class, self.expected_artifact, self.falsifier, self.writeback_plan, self.owner)
        if not _nonempty(strings) or not self.source_signal_refs or not self.allowed_tools or not self.allowed_data_classes or not self.stop_conditions or self.time_budget_minutes <= 0 or self.compute_budget <= 0 or self.estimated_cost < 0 or self.evidence_value < 0 or self.action_kind != "SYNTHETIC_FIXED_ACTION":
            raise SupervisorError("SLICE_FROZEN_CONTRACT_INCOMPLETE")
        if self.priority not in {Priority.P3_BOUNDED_IMPROVEMENT, Priority.P4_RESEARCH}:
            raise SupervisorError("SLICE_PRIORITY_NOT_IMPROVEMENT_CLASS")
        if not self.changed_paths or not set(self.changed_paths).issubset(snapshot.allowed_write_paths):
            raise SupervisorError("SLICE_CHANGED_PATH_OUTSIDE_ALLOWLIST")
        if _normalized(self.goal) in _INVALID_GOALS:
            raise SupervisorError("SLICE_INVALID_GOAL")
        if any(any(token in _normalized(tool) for token in _FORBIDDEN_TOOL_TOKENS) for tool in self.allowed_tools) or not set(self.allowed_tools).issubset(_STAGE_A_TOOL_CEILING):
            raise SupervisorError("SLICE_FORBIDDEN_TOOL")
        if not set(self.allowed_tools).issubset(set(snapshot.allowed_tools)):
            raise SupervisorError("SLICE_TOOL_POLICY_DRIFT")
        if any(any(token in _normalized(data_class) for token in _FORBIDDEN_DATA_TOKENS) for data_class in self.allowed_data_classes) or not set(self.allowed_data_classes).issubset(_STAGE_A_DATA_CEILING):
            raise SupervisorError("SLICE_FORBIDDEN_DATA_CLASS")
        if not set(self.allowed_data_classes).issubset(set(snapshot.allowed_data_classes)):
            raise SupervisorError("SLICE_DATA_POLICY_DRIFT")
        if any(token in _normalized(self.risk_class) for token in _FORBIDDEN_RISK_TOKENS) or self.risk_class not in _STAGE_A_RISK_CEILING:
            raise SupervisorError("SLICE_FORBIDDEN_RISK_CLASS")
        if self.risk_class not in snapshot.allowed_risk_classes:
            raise SupervisorError("SLICE_RISK_POLICY_DRIFT")
        if self.writeback_plan not in _STAGE_A_WRITEBACK_CEILING:
            raise SupervisorError("SLICE_FORBIDDEN_WRITEBACK")
        if self.writeback_plan not in snapshot.allowed_writeback_plans:
            raise SupervisorError("SLICE_WRITEBACK_POLICY_DRIFT")
        if (self.authority_metadata or {}).get("authority") in {"trusted", "provider-issued"}:
            raise SupervisorError("CALLER_AUTHORITY_UNTRUSTED")


@dataclass(frozen=True)
class LeaseGrant:
    slice_id: str
    owner: str
    generation: int
    fencing_token: str


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    snapshot: ReconciliationGrant
    slice: ImprovementSlice


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    mission_id: str
    slice_id: str
    plan_id: str
    slice_digest: str
    state: str
    created_at: int
    control_plane_snapshot_ref: str
    source_refs: tuple[str, ...]
    evidence_digests: tuple[str, ...]
    completed_atomic_steps: tuple[str, ...]
    open_unknowns: tuple[str, ...]
    next_atomic_action: str
    budget_state: str
    lease_state: str
    fencing_token_ref: str
    interruption_reason: str
    resume_preconditions: tuple[str, ...]
    privacy_class: str
    snapshot_identity: str
    reconciliation_generation: int
    prior_lease_generation: int
    exact_head: str
    route_id: str
    domain_revision: str

    def validate(self) -> None:
        strings = (self.checkpoint_id, self.mission_id, self.slice_id, self.plan_id, self.slice_digest, self.state, self.control_plane_snapshot_ref, self.next_atomic_action, self.budget_state, self.lease_state, self.fencing_token_ref, self.interruption_reason, self.privacy_class, self.snapshot_identity, self.exact_head, self.route_id, self.domain_revision)
        if not _nonempty(strings) or not self.source_refs or not self.evidence_digests or not self.completed_atomic_steps or not self.open_unknowns or not self.resume_preconditions or self.reconciliation_generation <= 0 or self.prior_lease_generation <= 0:
            raise SupervisorError("CHECKPOINT_FROZEN_CONTRACT_INCOMPLETE")
        if self.privacy_class != "PUBLIC_SAFE_SYNTHETIC":
            raise SupervisorError("CHECKPOINT_PRIVACY_NOT_PUBLIC_SAFE")
        if not _REQUIRED_RESUME_PRECONDITIONS.issubset(set(self.resume_preconditions)):
            raise SupervisorError("CHECKPOINT_RESUME_PRECONDITIONS_INCOMPLETE")


@dataclass(frozen=True)
class ReviewWorkIdentity:
    semantic_event_key: str
    target_head: str
    reconciliation_identity: str
    reconciliation_generation: int

    def key(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class ReviewEvidence:
    target_head: str
    ci_head: str
    receipt_head: str
    reviewer_source: str
    work: ReviewWorkIdentity


@dataclass(frozen=True)
class SupervisorReceipt:
    decision: Decision
    state: SupervisorState
    reason: str
    checkpoint_id: str | None = None
    process_compliance: str = "UNKNOWN"
    outcome_quality: str = "UNKNOWN"


@dataclass(frozen=True)
class StarvationStatus:
    slice_id: str
    counter: int
    original_priority: Priority
    effective_priority: Priority
    aged: bool
    materiality_eligible: bool
    fresh_reconciliation: bool
    promoted: bool
    reason: str



__all__ = tuple(name for name in globals() if not name.startswith("__"))
