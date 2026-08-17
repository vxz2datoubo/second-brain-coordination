"""R141 Stage-A supervisor entrypoint with B16/B17 bounded governance extensions.

The core module is the byte-preserved prior B13-B15 implementation. This
entrypoint remains the single public runtime surface and adds only task-local,
synthetic P2 recurrence and starvation/fairness bookkeeping.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import iagl_synthetic_supervisor_core as _core
from iagl_synthetic_supervisor_core import *

_ALLOWED = _core._ALLOWED
_P2_EVENT_CLASSES = _core._P2_EVENT_CLASSES
_normalized = _core._normalized
_STARVATION_THRESHOLD = 2


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


class WorkingStateStore(_core.WorkingStateStore):
    """Prior durable store plus B16 lifecycle and B17 starvation records."""

    def __init__(self, path):
        super().__init__(path)
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS p2_lifecycle_history (
          history_id TEXT PRIMARY KEY,
          event_key TEXT NOT NULL,
          transition TEXT NOT NULL,
          evidence_ref TEXT NOT NULL,
          reconciliation_identity TEXT NOT NULL,
          reconciliation_generation INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS starvation (
          slice_id TEXT PRIMARY KEY,
          counter INTEGER NOT NULL,
          last_seen_generation INTEGER NOT NULL,
          last_reason TEXT NOT NULL
        );
        """)
        self.connection.commit()

    def _record_p2_lifecycle(self, event_key: str, transition: str, evidence_ref: str, grant: ReconciliationGrant) -> None:
        history_id = digest({
            "event_key": event_key,
            "transition": transition,
            "evidence_ref": evidence_ref,
            "identity": grant.identity,
            "generation": grant.generation,
        })
        self.connection.execute(
            "INSERT OR IGNORE INTO p2_lifecycle_history VALUES (?,?,?,?,?,?)",
            (history_id, event_key, transition, evidence_ref, grant.identity, grant.generation),
        )

    def _reactivate_resolved_p2(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant) -> None:
        active_keys = set(snapshot.active_p2_event_keys)
        active_classes = {item.upper() for item in snapshot.active_p2_classes}
        if not active_keys and not active_classes:
            return
        rows = self.connection.execute(
            "SELECT semantic_key,event_json FROM events WHERE state='RESOLVED_TRACE'"
        ).fetchall()
        for semantic_key, raw in rows:
            event = _core._event_from_json(raw)
            event_class = event.event_class.upper()
            is_p2 = event_class in _P2_EVENT_CLASSES or event.class_priority_hint == Priority.P2_BLOCKER_OR_DRIFT
            if is_p2 and (semantic_key in active_keys or event_class in active_classes):
                self.connection.execute(
                    "UPDATE events SET priority=?,adjudication_generation=?,state='PENDING' WHERE semantic_key=?",
                    (int(Priority.P2_BLOCKER_OR_DRIFT), grant.generation, semantic_key),
                )
                self._record_p2_lifecycle(
                    semantic_key,
                    "REACTIVATED",
                    snapshot.p2_observation_ref or "POSITIVE_ACTIVE_SET",
                    grant,
                )

    def _adjudicate_pending_events(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant, prior_snapshot: ReconciliationSnapshot | None) -> None:
        self._reactivate_resolved_p2(snapshot, grant)
        super()._adjudicate_pending_events(snapshot, grant, prior_snapshot)
        resolutions = {item.event_key: item for item in snapshot.p2_resolutions}
        for event_key, resolution in resolutions.items():
            row = self.connection.execute(
                "SELECT state,adjudication_generation FROM events WHERE semantic_key=?",
                (event_key,),
            ).fetchone()
            if row == ("RESOLVED_TRACE", grant.generation):
                self._record_p2_lifecycle(
                    event_key,
                    "RESOLVED",
                    f"{snapshot.p2_observation_ref}|{resolution.resolution_ref}",
                    grant,
                )

    def p2_lifecycle(self, semantic_key: str) -> tuple[str, ...]:
        rows = self.connection.execute(
            "SELECT transition FROM p2_lifecycle_history WHERE event_key=? ORDER BY reconciliation_generation,transition",
            (semantic_key,),
        ).fetchall()
        return tuple(row[0] for row in rows)

    def _starvation_row(self, slice_id: str) -> tuple[int, int, str] | None:
        row = self.connection.execute(
            "SELECT counter,last_seen_generation,last_reason FROM starvation WHERE slice_id=?",
            (slice_id,),
        ).fetchone()
        return (int(row[0]), int(row[1]), str(row[2])) if row else None

    def starvation_status(self, slice_: ImprovementSlice, generation: int) -> StarvationStatus:
        row = self._starvation_row(slice_.slice_id)
        counter = row[0] if row else 0
        last_seen = row[1] if row else -1
        aged = counter >= _STARVATION_THRESHOLD
        material = _normalized(slice_.materiality) == "material"
        fresh = last_seen < generation
        promoted = bool(aged and material and fresh and slice_.priority == Priority.P4_RESEARCH)
        effective = Priority.P3_BOUNDED_IMPROVEMENT if promoted else slice_.priority
        if aged and material and fresh:
            reason = (
                "AGING+MATERIALITY+FRESH_RECONCILIATION:P4_TO_P3"
                if promoted else
                "AGING+MATERIALITY+FRESH_RECONCILIATION:P3_WITHIN_CLASS"
            )
        elif aged and not material:
            reason = "AGING_PRESENT:MATERIALITY_REQUIRED"
        elif aged and not fresh:
            reason = "AGING_PRESENT:FRESH_RECONCILIATION_REQUIRED"
        else:
            reason = f"AGING_COUNTER:{counter}/{_STARVATION_THRESHOLD}"
        return StarvationStatus(
            slice_.slice_id, counter, slice_.priority, effective,
            aged, material, fresh, promoted, reason,
        )

    def starvation_visibility(self, candidates: Sequence[ImprovementSlice], generation: int) -> tuple[StarvationStatus, ...]:
        statuses = [self.starvation_status(item, generation) for item in candidates]
        return tuple(sorted((item for item in statuses if item.counter > 0), key=lambda item: item.slice_id))

    def record_starvation_selection(self, candidates: Sequence[ImprovementSlice], selected_id: str, generation: int) -> None:
        for item in candidates:
            row = self._starvation_row(item.slice_id)
            counter = row[0] if row else 0
            last_seen = row[1] if row else -1
            if last_seen == generation:
                continue
            if item.slice_id == selected_id:
                new_counter, reason = 0, f"SELECTED:g{generation}"
            else:
                new_counter, reason = counter + 1, f"AGED_AFTER_SKIP:{counter + 1}:g{generation}"
            self.connection.execute(
                "INSERT INTO starvation VALUES (?,?,?,?) "
                "ON CONFLICT(slice_id) DO UPDATE SET "
                "counter=excluded.counter,last_seen_generation=excluded.last_seen_generation,last_reason=excluded.last_reason",
                (item.slice_id, new_counter, generation, reason),
            )
        self.connection.commit()


class SyntheticSupervisor(_core.SyntheticSupervisor):
    """Single public supervisor entrypoint retaining all core safety gates."""

    def starvation_visibility(self, grant: ReconciliationGrant, candidates: Sequence[ImprovementSlice]) -> tuple[StarvationStatus, ...]:
        current = self.store.current_snapshot()
        if not current or current[0] != grant:
            raise SupervisorError("STALE_RECONCILIATION_GRANT")
        for candidate in candidates:
            candidate.validate(current[1])
        return self.store.starvation_visibility(candidates, grant.generation)

    def choose(self, grant: ReconciliationGrant, candidates: Sequence[ImprovementSlice]) -> ExecutionPlan | ReviewWorkIdentity | SupervisorReceipt:
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
        statuses = {
            candidate.slice_id: self.store.starvation_status(candidate, grant.generation)
            for candidate in candidates
        }
        def fairness_key(item: ImprovementSlice):
            status = statuses[item.slice_id]
            aging_rank = (
                status.counter
                if status.aged and status.materiality_eligible and status.fresh_reconciliation
                else 0
            )
            return (int(status.effective_priority), -aging_rank, int(item.priority), item.slice_id)
        selected = min(candidates, key=fairness_key)
        if self.store.value("budget_used") + selected.estimated_cost > self.budget_limit:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
            return SupervisorReceipt(Decision.IDLE, self.state, "BUDGET_EXHAUSTED_PRE_EXECUTION")
        self.store.record_starvation_selection(candidates, selected.slice_id, grant.generation)
        return self.store.create_plan(grant, selected)
