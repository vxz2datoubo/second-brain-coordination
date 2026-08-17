"""Offline, deterministic, synthetic-only IAGL Stage-A supervisor.

Only this module defines the instantiable WorkingStateStore and SyntheticSupervisor.
Helper modules are contracts or unbound operation functions and cannot replace either runtime class.
"""
from __future__ import annotations

from _iagl_contracts import *
from _iagl_migrations import audit_legacy_reconciliation_snapshot
from _iagl_store_ops1 import (
    store__occurrence_key,
    store__remember_occurrence,
    store__backfill_event_occurrences,
    store__backfill_p0_gates,
    store__advance_p0_gate,
    store_current_p0_approval,
    store_occurrence_idempotencies,
    store_close,
    store_current_snapshot,
    store__trace,
    store_trace_sources,
    store_trace_classes,
    store_enqueue,
    store__ensure_head_delta_event,
    store__materialize_authoritative_p2,
)
from _iagl_store_ops2 import (
    store__record_p2_lifecycle,
    store__reactivate_resolved_p2,
    store_record_reconciliation,
    store__adjudicate_pending_events,
    store_p2_lifecycle,
    store_p0_disposition_history,
    store_p0_disposition_attempt_history,
    store_has_unadjudicated_events,
    store_highest_event,
    store_highest_preemption_event,
    store_current_p1_event,
    store_event_state,
    store_event_priority,
)
from _iagl_store_ops3 import (
    store_create_review_work,
    store_head_is_reviewed,
    store_consume_review_work,
    store_acquire_lease,
    store__lease_matches,
    store_execution_is_active,
    store_release_lease,
    store_create_plan,
    store_checkpointed_slice,
    store_authorize_execution,
    store_value,
)
from _iagl_store_ops4 import (
    store_set_value,
    store_save_checkpoint,
    store_load_checkpoint,
    store_issue_retrieval_complete_empty,
    store_consume_retrieval_proof,
    store__starvation_row,
    store_starvation_status,
    store_starvation_visibility,
    store_record_starvation_selection,
)
from _iagl_supervisor_ops1 import (
    supervisor_transition,
    supervisor_reconcile,
    supervisor_ingest,
    supervisor_starvation_visibility,
    supervisor_choose,
    supervisor_issue_retrieval_complete_empty_proof,
    supervisor_resolve_recall,
)
from _iagl_supervisor_ops2 import (
    supervisor_execute,
    supervisor_complete_atomic_slice,
    supervisor_safepoint,
    supervisor_checkpoint_for_preemption,
    supervisor_review,
    supervisor_resume_or_replan,
)


class WorkingStateStore:
    """The only current instantiable R141 working-state store."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS reconciliation (slot INTEGER PRIMARY KEY CHECK(slot=1), identity TEXT NOT NULL, generation INTEGER NOT NULL, snapshot TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (semantic_key TEXT PRIMARY KEY, event_json TEXT NOT NULL, priority INTEGER NOT NULL, adjudication_generation INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'PENDING');
        CREATE TABLE IF NOT EXISTS event_traces (trace_id TEXT PRIMARY KEY, semantic_key TEXT NOT NULL, source TEXT NOT NULL, event_class TEXT NOT NULL, target_identity TEXT NOT NULL, payload_digest TEXT NOT NULL, observed_at INTEGER NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS event_occurrences (occurrence_key TEXT PRIMARY KEY, semantic_key TEXT NOT NULL, idempotency_key TEXT NOT NULL, event_id TEXT NOT NULL, source TEXT NOT NULL, first_observed_at INTEGER NOT NULL, UNIQUE(semantic_key,idempotency_key));
        CREATE TABLE IF NOT EXISTS review_work (work_key TEXT PRIMARY KEY, semantic_key TEXT NOT NULL UNIQUE, target_head TEXT NOT NULL, identity TEXT NOT NULL, generation INTEGER NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviewed_heads (target_head TEXT PRIMARY KEY, work_key TEXT NOT NULL, reviewed_generation INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS p0_gates (event_key TEXT PRIMARY KEY, current_occurrence_key TEXT NOT NULL, approval_epoch INTEGER NOT NULL, coalesced_occurrences INTEGER NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS p0_disposition_history (history_id TEXT PRIMARY KEY, event_key TEXT NOT NULL, decision TEXT NOT NULL, decision_ref TEXT NOT NULL, reconciliation_identity TEXT NOT NULL, reconciliation_generation INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS p0_disposition_attempt_history (attempt_id TEXT PRIMARY KEY, event_key TEXT NOT NULL, decision TEXT NOT NULL, decision_ref TEXT NOT NULL, supplied_occurrence_key TEXT NOT NULL, supplied_approval_epoch INTEGER NOT NULL, current_occurrence_key TEXT NOT NULL, current_approval_epoch INTEGER NOT NULL, outcome TEXT NOT NULL, reconciliation_identity TEXT NOT NULL, reconciliation_generation INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS p2_resolution_history (event_key TEXT PRIMARY KEY, resolution_ref TEXT NOT NULL, observation_ref TEXT NOT NULL, reconciliation_identity TEXT NOT NULL, reconciliation_generation INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS p2_lifecycle_history (history_id TEXT PRIMARY KEY, event_key TEXT NOT NULL, transition TEXT NOT NULL, evidence_ref TEXT NOT NULL, reconciliation_identity TEXT NOT NULL, reconciliation_generation INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS starvation (slice_id TEXT PRIMARY KEY, counter INTEGER NOT NULL, last_seen_generation INTEGER NOT NULL, last_reason TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS leases (slice_id TEXT PRIMARY KEY, owner TEXT NOT NULL, generation INTEGER NOT NULL, token TEXT NOT NULL, active INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS plans (plan_id TEXT PRIMARY KEY, identity TEXT NOT NULL, generation INTEGER NOT NULL, slice_json TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS checkpoints (checkpoint_id TEXT PRIMARY KEY, record TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS retrieval_proofs (issuance_ref TEXT PRIMARY KEY, proof_digest TEXT NOT NULL, provider_observation_digest TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS accounting (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
        """)
        self._backfill_event_occurrences()
        self._backfill_p0_gates()
        audit_legacy_reconciliation_snapshot(self)
        self.connection.commit()

    _occurrence_key = staticmethod(store__occurrence_key)
    _remember_occurrence = store__remember_occurrence
    _backfill_event_occurrences = store__backfill_event_occurrences
    _backfill_p0_gates = store__backfill_p0_gates
    _advance_p0_gate = store__advance_p0_gate
    current_p0_approval = store_current_p0_approval
    occurrence_idempotencies = store_occurrence_idempotencies
    close = store_close
    current_snapshot = store_current_snapshot
    _trace = store__trace
    trace_sources = store_trace_sources
    trace_classes = store_trace_classes
    enqueue = store_enqueue
    _ensure_head_delta_event = store__ensure_head_delta_event
    _materialize_authoritative_p2 = store__materialize_authoritative_p2
    _record_p2_lifecycle = store__record_p2_lifecycle
    _reactivate_resolved_p2 = store__reactivate_resolved_p2
    record_reconciliation = store_record_reconciliation
    _adjudicate_pending_events = store__adjudicate_pending_events
    p2_lifecycle = store_p2_lifecycle
    p0_disposition_history = store_p0_disposition_history
    p0_disposition_attempt_history = store_p0_disposition_attempt_history
    has_unadjudicated_events = store_has_unadjudicated_events
    highest_event = store_highest_event
    highest_preemption_event = store_highest_preemption_event
    current_p1_event = store_current_p1_event
    event_state = store_event_state
    event_priority = store_event_priority
    create_review_work = store_create_review_work
    head_is_reviewed = store_head_is_reviewed
    consume_review_work = store_consume_review_work
    acquire_lease = store_acquire_lease
    _lease_matches = store__lease_matches
    execution_is_active = store_execution_is_active
    release_lease = store_release_lease
    create_plan = store_create_plan
    checkpointed_slice = store_checkpointed_slice
    authorize_execution = store_authorize_execution
    value = store_value
    set_value = store_set_value
    save_checkpoint = store_save_checkpoint
    load_checkpoint = store_load_checkpoint
    issue_retrieval_complete_empty = store_issue_retrieval_complete_empty
    consume_retrieval_proof = store_consume_retrieval_proof
    _starvation_row = store__starvation_row
    starvation_status = store_starvation_status
    starvation_visibility = store_starvation_visibility
    record_starvation_selection = store_record_starvation_selection


class SyntheticSupervisor:
    """The only current instantiable R141 supervisor behavior."""

    def __init__(self, repository: str, store: WorkingStateStore, budget_limit: int = 8, no_value_limit: int = 10, retrieval_provider: SyntheticRetrievalProvider | None = None):
        if type(store) is not WorkingStateStore:
            raise SupervisorError("CANONICAL_WORKING_STATE_STORE_REQUIRED")
        self.repository = repository
        self.store = store
        self.budget_limit = budget_limit
        self.no_value_limit = no_value_limit
        self.retrieval_provider = retrieval_provider or SyntheticRetrievalProvider()
        self.state = SupervisorState.BOOT

    transition = supervisor_transition
    reconcile = supervisor_reconcile
    ingest = supervisor_ingest
    starvation_visibility = supervisor_starvation_visibility
    choose = supervisor_choose
    issue_retrieval_complete_empty_proof = supervisor_issue_retrieval_complete_empty_proof
    resolve_recall = supervisor_resolve_recall
    execute = supervisor_execute
    complete_atomic_slice = supervisor_complete_atomic_slice
    safepoint = supervisor_safepoint
    checkpoint_for_preemption = supervisor_checkpoint_for_preemption
    review = supervisor_review
    resume_or_replan = supervisor_resume_or_replan
