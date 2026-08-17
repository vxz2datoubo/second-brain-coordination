from __future__ import annotations

from _iagl_contracts import *

def store__record_p2_lifecycle(self, event_key: str, transition: str, evidence_ref: str, grant: ReconciliationGrant) -> None:
    history_id = digest({"event_key": event_key, "transition": transition, "evidence_ref": evidence_ref, "identity": grant.identity, "generation": grant.generation})
    self.connection.execute(
        "INSERT OR IGNORE INTO p2_lifecycle_history VALUES (?,?,?,?,?,?)",
        (history_id, event_key, transition, evidence_ref, grant.identity, grant.generation),
    )

def store__reactivate_resolved_p2(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant) -> None:
    active_keys = set(snapshot.active_p2_event_keys)
    active_classes = {item.upper() for item in snapshot.active_p2_classes}
    if not active_keys and not active_classes:
        return
    rows = self.connection.execute("SELECT semantic_key,event_json FROM events WHERE state='RESOLVED_TRACE'").fetchall()
    for semantic_key, raw in rows:
        event = _event_from_json(raw)
        event_class = event.event_class.upper()
        is_p2 = event_class in _P2_EVENT_CLASSES or event.class_priority_hint == Priority.P2_BLOCKER_OR_DRIFT
        if is_p2 and (semantic_key in active_keys or event_class in active_classes):
            self.connection.execute(
                "UPDATE events SET priority=?,adjudication_generation=?,state='PENDING' WHERE semantic_key=?",
                (int(Priority.P2_BLOCKER_OR_DRIFT), grant.generation, semantic_key),
            )
            self._record_p2_lifecycle(semantic_key, "REACTIVATED", snapshot.p2_observation_ref or "POSITIVE_ACTIVE_SET", grant)

def store_record_reconciliation(self, snapshot: ReconciliationSnapshot) -> ReconciliationGrant:
    prior = self.current_snapshot()
    prior_snapshot = prior[1] if prior else None
    row = self.connection.execute("SELECT generation FROM reconciliation WHERE slot=1").fetchone()
    generation = (row[0] if row else 0) + 1
    identity = snapshot.identity()
    self.connection.execute(
        "INSERT INTO reconciliation VALUES (1,?,?,?) ON CONFLICT(slot) DO UPDATE SET identity=excluded.identity,generation=excluded.generation,snapshot=excluded.snapshot",
        (identity, generation, _snapshot_to_json(snapshot)),
    )
    grant = ReconciliationGrant(identity, generation)
    self._ensure_head_delta_event(snapshot, prior_snapshot)
    self._materialize_authoritative_p2(snapshot)
    self._reactivate_resolved_p2(snapshot, grant)
    self._adjudicate_pending_events(snapshot, grant, prior_snapshot)
    self.connection.commit()
    return grant

def store__adjudicate_pending_events(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant, prior_snapshot: ReconciliationSnapshot | None) -> None:
    active_keys = set(snapshot.active_p2_event_keys)
    active_classes = {item.upper() for item in snapshot.active_p2_classes}
    dispositions = {item.event_key: item for item in snapshot.p0_dispositions}
    resolutions = {item.event_key: item for item in snapshot.p2_resolutions}
    rows = self.connection.execute("SELECT semantic_key,event_json FROM events WHERE state='PENDING'").fetchall()
    for semantic_key, raw in rows:
        event = _event_from_json(raw)
        event_class = event.event_class.upper()
        if event.risk_markers or event_class in _P0_EVENT_CLASSES:
            disposition = dispositions.get(semantic_key)
            disposition_is_fresh = bool(
                disposition is not None
                and not self.connection.execute(
                    "SELECT 1 FROM p0_disposition_history WHERE event_key=? AND decision_ref=? LIMIT 1",
                    (semantic_key, disposition.decision_ref),
                ).fetchone()
            )
            if disposition_is_fresh:
                priority, state = Priority.P0_USER_OR_HIGH_RISK, "P0_DISPOSITION_TRACE"
                history_id = digest({"event_key": semantic_key, "decision_ref": disposition.decision_ref, "identity": grant.identity, "generation": grant.generation})
                self.connection.execute(
                    "INSERT OR IGNORE INTO p0_disposition_history VALUES (?,?,?,?,?,?)",
                    (history_id, semantic_key, disposition.decision, disposition.decision_ref, grant.identity, grant.generation),
                )
            else:
                priority, state = Priority.P0_USER_OR_HIGH_RISK, "PENDING"
        elif event.semantic_kind == "HEAD_OBSERVATION":
            if event.target_identity != snapshot.exact_head or self.head_is_reviewed(snapshot.exact_head):
                priority, state = Priority.P1_EXACT_HEAD_REVIEW, "TRACE_ONLY"
            else:
                trace_classes = set(self.trace_classes(semantic_key))
                head_delta = bool(prior_snapshot and prior_snapshot.exact_head != snapshot.exact_head)
                explicit_head_event = "PR_HEAD_CHANGED" in trace_classes or "RECONCILIATION_HEAD_DELTA" in trace_classes
                priority, state = (Priority.P1_EXACT_HEAD_REVIEW, "PENDING") if (head_delta or explicit_head_event) else (Priority.P4_RESEARCH, "PENDING")
        elif event_class in _P1_EVENT_CLASSES:
            priority, state = (Priority.P1_EXACT_HEAD_REVIEW, "PENDING") if event.target_identity == snapshot.exact_head else (Priority.P1_EXACT_HEAD_REVIEW, "TRACE_ONLY")
        elif event_class in _P2_EVENT_CLASSES or event.class_priority_hint == Priority.P2_BLOCKER_OR_DRIFT:
            if semantic_key in active_keys or event_class in active_classes:
                priority, state = Priority.P2_BLOCKER_OR_DRIFT, "PENDING"
            elif snapshot.p2_observation_status == "AUTHORITATIVE_COMPLETE" and semantic_key in resolutions:
                resolution = resolutions[semantic_key]
                priority, state = Priority.P2_BLOCKER_OR_DRIFT, "RESOLVED_TRACE"
                self.connection.execute(
                    "INSERT OR REPLACE INTO p2_resolution_history VALUES (?,?,?,?,?)",
                    (semantic_key, resolution.resolution_ref, snapshot.p2_observation_ref, grant.identity, grant.generation),
                )
                self._record_p2_lifecycle(semantic_key, "RESOLVED", f"{snapshot.p2_observation_ref}|{resolution.resolution_ref}", grant)
            else:
                priority, state = Priority.P2_BLOCKER_OR_DRIFT, "PENDING"
        elif event_class in _P3_EVENT_CLASSES:
            priority, state = Priority.P3_BOUNDED_IMPROVEMENT, "PENDING"
        elif event_class in _P4_EVENT_CLASSES:
            priority, state = Priority.P4_RESEARCH, "PENDING"
        else:
            priority, state = Priority.P2_BLOCKER_OR_DRIFT, "PENDING"
        self.connection.execute(
            "UPDATE events SET priority=?,adjudication_generation=?,state=? WHERE semantic_key=?",
            (int(priority), grant.generation, state, semantic_key),
        )

def store_p2_lifecycle(self, semantic_key: str) -> tuple[str, ...]:
    rows = self.connection.execute(
        "SELECT transition FROM p2_lifecycle_history WHERE event_key=? ORDER BY reconciliation_generation,transition",
        (semantic_key,),
    ).fetchall()
    return tuple(row[0] for row in rows)

def store_p0_disposition_history(self, semantic_key: str) -> tuple[tuple[str, str], ...]:
    rows = self.connection.execute(
        "SELECT decision,decision_ref FROM p0_disposition_history WHERE event_key=? ORDER BY reconciliation_generation,history_id",
        (semantic_key,),
    ).fetchall()
    return tuple((row[0], row[1]) for row in rows)

def store_has_unadjudicated_events(self, generation: int) -> bool:
    return bool(self.connection.execute("SELECT 1 FROM events WHERE state='PENDING' AND adjudication_generation<>? LIMIT 1", (generation,)).fetchone())

def store_highest_event(self, generation: int) -> NormalizedEvent | None:
    row = self.connection.execute("SELECT event_json FROM events WHERE state='PENDING' AND adjudication_generation=? ORDER BY priority,semantic_key LIMIT 1", (generation,)).fetchone()
    return _event_from_json(row[0]) if row else None

def store_highest_preemption_event(self, generation: int, work_priority: Priority) -> tuple[NormalizedEvent, Priority] | None:
    rows = self.connection.execute("SELECT event_json,priority,adjudication_generation FROM events WHERE state='PENDING' ORDER BY semantic_key").fetchall()
    candidates: list[tuple[Priority, str, NormalizedEvent]] = []
    for raw, priority_raw, adjudication_generation in rows:
        event = _event_from_json(raw)
        effective = Priority(priority_raw) if adjudication_generation == generation else (Priority.P0_USER_OR_HIGH_RISK if event.risk_markers else Priority.P2_BLOCKER_OR_DRIFT)
        if effective < work_priority:
            candidates.append((effective, event.semantic_key, event))
    if not candidates:
        return None
    effective, _key, event = min(candidates, key=lambda item: (int(item[0]), item[1]))
    return event, effective

def store_current_p1_event(self, exact_head: str, generation: int) -> NormalizedEvent | None:
    rows = self.connection.execute("SELECT event_json FROM events WHERE priority=1 AND adjudication_generation=? AND state='PENDING' ORDER BY semantic_key", (generation,)).fetchall()
    for row in rows:
        event = _event_from_json(row[0])
        if event.target_identity == exact_head:
            return event
    return None

def store_event_state(self, semantic_key: str) -> str | None:
    row = self.connection.execute("SELECT state FROM events WHERE semantic_key=?", (semantic_key,)).fetchone()
    return row[0] if row else None

def store_event_priority(self, semantic_key: str) -> Priority | None:
    row = self.connection.execute("SELECT priority FROM events WHERE semantic_key=?", (semantic_key,)).fetchone()
    return Priority(row[0]) if row else None

