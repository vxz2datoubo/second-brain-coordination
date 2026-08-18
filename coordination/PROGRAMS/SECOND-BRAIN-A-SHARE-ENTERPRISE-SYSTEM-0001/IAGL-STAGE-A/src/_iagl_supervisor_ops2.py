from __future__ import annotations

from _iagl_contracts import *

def supervisor_execute(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
    if self.state != SupervisorState.CHECK_PRIORITY:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "EXECUTION_NOT_AT_RECONCILED_PRIORITY_BOUNDARY")
    if self.store.has_unadjudicated_events(plan.snapshot.generation):
        return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT")
    pending = self.store.highest_event(plan.snapshot.generation)
    if pending and (self.store.event_priority(pending.semantic_key) or Priority.P4_RESEARCH) < plan.slice.priority:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "HIGHER_PRIORITY_PENDING_AT_EXECUTION")
    authorized = self.store.authorize_execution(plan, lease, self.budget_limit)
    if not authorized:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "EXECUTION_BOUNDARY_REJECTED")
    self.transition(SupervisorState.WORK_SLICE)
    return SupervisorReceipt(Decision.EXECUTED, self.state, "SYNTHETIC_ATOMIC_ACTION", process_compliance="PASS", outcome_quality="UNKNOWN")

def supervisor_complete_atomic_slice(self, evidence_value: int) -> SupervisorReceipt:
    if self.state != SupervisorState.WORK_SLICE:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "NOT_IN_WORK_SLICE")
    self.transition(SupervisorState.EVALUATE)
    self.store.set_value("no_value_streak", 0 if evidence_value else self.store.value("no_value_streak") + 1)
    return SupervisorReceipt(Decision.EXECUTED, self.state, "EVALUATED", outcome_quality="UNKNOWN")

def supervisor_safepoint(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
    return self.checkpoint_for_preemption(plan, lease)

def supervisor_checkpoint_for_preemption(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
    if self.state != SupervisorState.WORK_SLICE:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "SAFEPOINT_NOT_IN_WORK_SLICE")
    current = self.store.current_snapshot()
    if not current:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "RECONCILIATION_MISSING_AT_SAFEPOINT")
    preemption = self.store.highest_preemption_event(current[0].generation, plan.slice.priority)
    if not preemption:
        return SupervisorReceipt(Decision.UNKNOWN, self.state, "NO_PREEMPTION")
    event, effective_priority = preemption
    if plan.slice.slice_id != lease.slice_id or not self.store.execution_is_active(plan, lease):
        return SupervisorReceipt(Decision.BLOCKED, self.state, "STALE_OR_CROSS_SLICE_FENCE")
    grant, snapshot = current
    self.transition(SupervisorState.SAFEPOINT_CHECKPOINT)
    checkpoint = Checkpoint(
        checkpoint_id=digest({"plan": plan.plan_id, "slice_digest": _slice_digest(plan.slice), "event": event.semantic_key, "fence": lease.fencing_token}),
        mission_id="CODEX-IAGL-R141-STAGE-A-SYNTHETIC-SUPERVISOR", slice_id=plan.slice.slice_id,
        plan_id=plan.plan_id, slice_digest=_slice_digest(plan.slice), state=SupervisorState.SAFEPOINT_CHECKPOINT.value,
        created_at=snapshot.observed_at, control_plane_snapshot_ref=grant.identity,
        source_refs=(event.semantic_key,), evidence_digests=(event.payload_digest,),
        completed_atomic_steps=("SYNTHETIC_ATOMIC_ACTION",), open_unknowns=("OUTCOME_QUALITY_UNKNOWN",),
        next_atomic_action="FRESH_RECONCILE_AND_RESUME_OR_REPLAN", budget_state=f"used:{self.store.value('budget_used')}",
        lease_state=f"owner:{lease.owner};generation:{lease.generation}", fencing_token_ref=digest(lease.fencing_token),
        interruption_reason=f"priority:{int(effective_priority)}",
        resume_preconditions=("FRESH_RECONCILIATION", "AUTONOMOUS", "NO_PENDING_P0", "MATCHING_SLICE", "NEW_FENCE"),
        privacy_class="PUBLIC_SAFE_SYNTHETIC", snapshot_identity=grant.identity,
        reconciliation_generation=grant.generation, prior_lease_generation=lease.generation,
        exact_head=snapshot.exact_head, route_id=snapshot.route_id, domain_revision=snapshot.domain_revision,
    )
    self.store.save_checkpoint(checkpoint)
    self.store.release_lease(lease)
    self.transition(SupervisorState.PAUSED_FOR_HIGHER_PRIORITY)
    return SupervisorReceipt(Decision.PREEMPTED, self.state, "HIGHER_PRIORITY_PREEMPTION_AT_SAFEPOINT", checkpoint.checkpoint_id)

def supervisor_review(self, work: ReviewWorkIdentity, evidence: ReviewEvidence) -> SupervisorReceipt:
    if self.state == SupervisorState.PAUSED_FOR_HIGHER_PRIORITY:
        self.transition(SupervisorState.REVIEW)
    if self.state != SupervisorState.REVIEW:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "REVIEW_NOT_READY")
    current = self.store.current_snapshot()
    valid = bool(
        current and work == evidence.work
        and _nonempty((evidence.target_head, evidence.ci_head, evidence.receipt_head, evidence.reviewer_source))
        and work.target_head == evidence.target_head == evidence.ci_head == evidence.receipt_head == current[1].exact_head
        and work.reconciliation_identity == current[0].identity and work.reconciliation_generation == current[0].generation
        and self.store.consume_review_work(work, current[0])
    )
    if not valid:
        self.transition(SupervisorState.FAILED_CLOSED)
        return SupervisorReceipt(Decision.BLOCKED, self.state, "REVIEW_WORK_IDENTITY_OR_RECEIPT_MISMATCH")
    self.transition(SupervisorState.EVALUATE)
    return SupervisorReceipt(Decision.EXECUTED, self.state, "P1_REVIEW_EXACT_HEAD_VALID")

def supervisor_resume_or_replan(self, checkpoint_id: str, fresh: ReconciliationGrant, lease: LeaseGrant) -> SupervisorReceipt:
    try:
        checkpoint = self.store.load_checkpoint(checkpoint_id)
    except SupervisorError:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINT_RESUME_PRECONDITIONS_INVALID")
    current = self.store.current_snapshot()
    if not checkpoint or not current or current[0] != fresh or fresh.generation <= checkpoint.reconciliation_generation:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED")
    _, snapshot = current
    if self.store.has_unadjudicated_events(fresh.generation):
        return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT")
    if (
        checkpoint.slice_id != lease.slice_id or snapshot.governance_mode != GovernanceMode.AUTONOMOUS or snapshot.pending_p0
        or checkpoint.route_id != snapshot.route_id or checkpoint.domain_revision != snapshot.domain_revision
        or not _REQUIRED_RESUME_PRECONDITIONS.issubset(set(checkpoint.resume_preconditions))
    ):
        return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINT_DRIFT_OR_GOVERNANCE_OR_SLICE_GATE")
    slice_ = self.store.checkpointed_slice(checkpoint)
    if slice_ is None:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINT_PLAN_OR_SLICE_IDENTITY_MISMATCH")
    try:
        slice_.validate(snapshot)
    except SupervisorError:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINTED_SLICE_POLICY_DRIFT")
    pending = self.store.highest_event(fresh.generation)
    if pending and (self.store.event_priority(pending.semantic_key) or Priority.P4_RESEARCH) < slice_.priority:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "HIGHER_PRIORITY_PENDING_AT_RESUME")
    if self.state == SupervisorState.CHECK_PRIORITY:
        self.transition(SupervisorState.REVIEW)
        self.transition(SupervisorState.EVALUATE)
    if self.state == SupervisorState.EVALUATE:
        self.transition(SupervisorState.LEARN)
    if self.state != SupervisorState.LEARN:
        return SupervisorReceipt(Decision.BLOCKED, self.state, "RESUME_STATE_INVALID")
    self.transition(SupervisorState.RESUME_VALIDATION)
    if not self.store._lease_matches(lease) or lease.generation <= checkpoint.prior_lease_generation:
        self.transition(SupervisorState.FAILED_CLOSED)
        return SupervisorReceipt(Decision.BLOCKED, self.state, "STALE_OR_FORGED_OR_CROSS_SLICE_FENCE")
    self.transition(SupervisorState.RESUME)
    self.transition(SupervisorState.WORK_SLICE)
    return SupervisorReceipt(Decision.EXECUTED, self.state, "FRESH_RECONCILE_RESUME_OR_REPLAN", checkpoint_id)
