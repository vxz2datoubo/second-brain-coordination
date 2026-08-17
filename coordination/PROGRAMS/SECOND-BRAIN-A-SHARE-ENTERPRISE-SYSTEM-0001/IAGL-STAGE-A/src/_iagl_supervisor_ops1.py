from __future__ import annotations

from _iagl_contracts import *

def supervisor_transition(self, target: SupervisorState) -> None:
    if target not in _ALLOWED[self.state]:
        raise SupervisorError(f"ILLEGAL_TRANSITION:{self.state.value}->{target.value}")
    self.state = target

def supervisor_reconcile(self, snapshot: ReconciliationSnapshot) -> ReconciliationGrant:
    prior = self.store.current_snapshot()
    if self.state == SupervisorState.CHECK_PRIORITY:
        if prior and prior[1].governance_mode != snapshot.governance_mode:
            self.transition(SupervisorState.USER_GATE)
        else:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
    self.transition(SupervisorState.GLOBAL_RECONCILIATION)
    snapshot.validate(self.repository)
    if snapshot.governance_mode == GovernanceMode.EMERGENCY_STOP:
        self.transition(SupervisorState.EMERGENCY_STOP)
        raise SupervisorError("EMERGENCY_STOP")
    grant = self.store.record_reconciliation(snapshot)
    self.transition(SupervisorState.CHECK_PRIORITY)
    return grant

def supervisor_ingest(self, raw: Mapping[str, Any]) -> tuple[NormalizedEvent, bool]:
    event = NormalizedEvent.from_mapping(raw)
    if event.repository != self.repository:
        raise SupervisorError("EVENT_REPOSITORY_MISMATCH")
    return event, self.store.enqueue(event)

def supervisor_starvation_visibility(self, grant: ReconciliationGrant, candidates: Sequence[ImprovementSlice]) -> tuple[StarvationStatus, ...]:
    current = self.store.current_snapshot()
    if not current or current[0] != grant:
        raise SupervisorError("STALE_RECONCILIATION_GRANT")
    for candidate in candidates:
        candidate.validate(current[1])
    return self.store.starvation_visibility(candidates, grant.generation)

def supervisor_choose(self, grant: ReconciliationGrant, candidates: Sequence[ImprovementSlice]) -> ExecutionPlan | ReviewWorkIdentity | SupervisorReceipt:
    current = self.store.current_snapshot()
    if not current or current[0] != grant:
        raise SupervisorError("STALE_RECONCILIATION_GRANT")
    _, snapshot = current
    if self.store.has_unadjudicated_events(grant.generation):
        self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
        return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT")
    pending = self.store.highest_event(grant.generation)
    pending_priority = self.store.event_priority(pending.semantic_key) if pending else None
    if snapshot.governance_mode != GovernanceMode.AUTONOMOUS or snapshot.pending_p0 or pending_priority == Priority.P0_USER_OR_HIGH_RISK:
        self.transition(SupervisorState.USER_GATE)
        return SupervisorReceipt(Decision.USER_GATE, self.state, "GOVERNANCE_OR_P0_GATE")
    event = self.store.current_p1_event(snapshot.exact_head, grant.generation)
    if event:
        self.transition(SupervisorState.REVIEW)
        return self.store.create_review_work(event, grant)
    pending = self.store.highest_event(grant.generation)
    if pending and self.store.event_priority(pending.semantic_key) == Priority.P2_BLOCKER_OR_DRIFT:
        self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
        return SupervisorReceipt(Decision.BLOCKED, self.state, "P2_PARTIAL_OR_UNRESOLVED_AWAITING_AUTHORITY")
    if not candidates:
        if snapshot.eligible_work_queue_complete:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
            return SupervisorReceipt(Decision.IDLE, self.state, "TRUSTED_COMPLETE_EMPTY_WORK_QUEUE")
        return SupervisorReceipt(Decision.UNKNOWN, self.state, "ELIGIBLE_WORK_COMPLETENESS_UNPROVEN")
    if self.store.value("no_value_streak") >= self.no_value_limit:
        self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
        return SupervisorReceipt(Decision.IDLE, self.state, "VOI_STOP")
    for candidate in candidates:
        candidate.validate(snapshot)
    statuses = {candidate.slice_id: self.store.starvation_status(candidate, grant.generation) for candidate in candidates}

    def fairness_key(item: ImprovementSlice):
        status = statuses[item.slice_id]
        aging_rank = status.counter if status.aged and status.materiality_eligible and status.fresh_reconciliation else 0
        return (int(status.effective_priority), -aging_rank, int(item.priority), item.slice_id)

    selected = min(candidates, key=fairness_key)
    if self.store.value("budget_used") + selected.estimated_cost > self.budget_limit:
        self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
        return SupervisorReceipt(Decision.IDLE, self.state, "BUDGET_EXHAUSTED_PRE_EXECUTION")
    self.store.record_starvation_selection(candidates, selected.slice_id, grant.generation)
    return self.store.create_plan(grant, selected)

def supervisor_issue_retrieval_complete_empty_proof(self, grant: ReconciliationGrant, request_digest: str, authority_scope_ref: str) -> RetrievalCompletenessProof | None:
    current = self.store.current_snapshot()
    if not current or current[0] != grant:
        raise SupervisorError("RETRIEVAL_PROOF_ISSUANCE_REQUIRES_CURRENT_RECONCILIATION")
    observation = self.retrieval_provider.observe_complete_empty(self.repository, current[1].exact_head, request_digest, authority_scope_ref)
    if observation is None:
        return None
    return self.store.issue_retrieval_complete_empty(current[1], grant, observation)

def supervisor_resolve_recall(self, grant: ReconciliationGrant, request_digest: str, proof: RetrievalCompletenessProof | None) -> SupervisorReceipt:
    current = self.store.current_snapshot()
    if not current or current[0] != grant or proof is None:
        return SupervisorReceipt(Decision.UNKNOWN, self.state, "RETRIEVAL_COMPLETENESS_UNPROVEN", process_compliance="INCOMPLETE")
    if not proof.structurally_matches(current[1], grant, request_digest):
        return SupervisorReceipt(Decision.UNKNOWN, self.state, "RETRIEVAL_COMPLETENESS_UNPROVEN", process_compliance="INCOMPLETE")
    if not self.store.consume_retrieval_proof(proof, current[1], grant, request_digest):
        return SupervisorReceipt(Decision.UNKNOWN, self.state, "RETRIEVAL_COMPLETENESS_UNTRUSTED", process_compliance="UNTRUSTED")
    return SupervisorReceipt(Decision.IDLE, SupervisorState.IDLE_NO_ELIGIBLE_WORK, "TRUSTED_COMPLETE_EMPTY_RETRIEVAL", process_compliance="PASS")
