from __future__ import annotations

from _iagl_contracts import *

def store__occurrence_key(event: NormalizedEvent) -> str:
    # Synthetic Stage-A recurrence identity is deliberately bounded to the
    # semantic target state plus caller-supplied idempotency key. A future
    # live occurrence-attestation provider remains UNKNOWN-007.
    return digest({"semantic_key": event.semantic_key, "idempotency_key": event.supplied_idempotency_key})

def store__remember_occurrence(self, event: NormalizedEvent) -> bool:
    occurrence_key = self._occurrence_key(event)
    cur = self.connection.execute(
        "INSERT OR IGNORE INTO event_occurrences VALUES (?,?,?,?,?,?)",
        (occurrence_key, event.semantic_key, event.supplied_idempotency_key, event.event_id, event.source, event.observed_at),
    )
    return cur.rowcount == 1

def store__backfill_event_occurrences(self) -> None:
    # Upgrade safety: existing durable event rows predate B22. Preserve the
    # last stored occurrence as already-seen so an exact retry after restart
    # cannot spuriously reopen a previously disposed P0 occurrence.
    rows = self.connection.execute("SELECT event_json FROM events").fetchall()
    for (raw,) in rows:
        self._remember_occurrence(_event_from_json(raw))

def store_occurrence_idempotencies(self, semantic_key: str) -> tuple[str, ...]:
    rows = self.connection.execute(
        "SELECT idempotency_key FROM event_occurrences WHERE semantic_key=? ORDER BY first_observed_at,idempotency_key",
        (semantic_key,),
    ).fetchall()
    return tuple(row[0] for row in rows)

def store_close(self) -> None:
    self.connection.close()

def store_current_snapshot(self) -> tuple[ReconciliationGrant, ReconciliationSnapshot] | None:
    row = self.connection.execute("SELECT identity,generation,snapshot FROM reconciliation WHERE slot=1").fetchone()
    if not row:
        return None
    return ReconciliationGrant(row[0], row[1]), _snapshot_from_json(row[2])

def store__trace(self, event: NormalizedEvent, state: str = "OBSERVED") -> None:
    trace_id = digest({"event_id": event.event_id, "source": event.source, "class": event.event_class, "observed_at": event.observed_at, "idempotency": event.supplied_idempotency_key})
    self.connection.execute(
        "INSERT OR IGNORE INTO event_traces VALUES (?,?,?,?,?,?,?,?)",
        (trace_id, event.semantic_key, event.source, event.event_class, event.target_identity, event.payload_digest, event.observed_at, state),
    )

def store_trace_sources(self, semantic_key: str) -> tuple[str, ...]:
    rows = self.connection.execute("SELECT source FROM event_traces WHERE semantic_key=? ORDER BY source", (semantic_key,)).fetchall()
    return tuple(row[0] for row in rows)

def store_trace_classes(self, semantic_key: str) -> tuple[str, ...]:
    rows = self.connection.execute("SELECT event_class FROM event_traces WHERE semantic_key=? ORDER BY event_class", (semantic_key,)).fetchall()
    return tuple(row[0] for row in rows)

def store_enqueue(self, event: NormalizedEvent) -> bool:
    # Idempotency is evaluated before any P0 recurrence reactivation. The
    # same idempotency key for the same semantic target state is a transport
    # duplicate/redelivery even if the retry envelope has a new event_id or
    # observed_at. Only a new occurrence identity may reopen disposed P0.
    new_occurrence = self._remember_occurrence(event)
    self._trace(event, "OBSERVED" if new_occurrence else "DUPLICATE_REDELIVERY")
    row = self.connection.execute("SELECT state FROM events WHERE semantic_key=?", (event.semantic_key,)).fetchone()
    if row is not None:
        if not new_occurrence:
            self.connection.commit()
            return False
        if row[0] == "P0_DISPOSITION_TRACE" and (event.risk_markers or event.event_class.upper() in _P0_EVENT_CLASSES):
            self.connection.execute(
                "UPDATE events SET event_json=?,priority=?,adjudication_generation=0,state='PENDING' WHERE semantic_key=?",
                (_event_to_json(event), int(Priority.P0_USER_OR_HIGH_RISK), event.semantic_key),
            )
            self.connection.commit()
        else:
            self.connection.commit()
        return False
    provisional = Priority.P0_USER_OR_HIGH_RISK if event.risk_markers else Priority.P2_BLOCKER_OR_DRIFT
    self.connection.execute(
        "INSERT INTO events(semantic_key,event_json,priority,adjudication_generation,state) VALUES (?,?,?,?, 'PENDING')",
        (event.semantic_key, _event_to_json(event), int(provisional), 0),
    )
    self.connection.commit()
    return True

def store__ensure_head_delta_event(self, snapshot: ReconciliationSnapshot, prior_snapshot: ReconciliationSnapshot | None) -> None:
    if prior_snapshot is None or prior_snapshot.exact_head == snapshot.exact_head or self.head_is_reviewed(snapshot.exact_head):
        return
    event = NormalizedEvent.from_mapping({
        "event_id": f"reconcile-head:{snapshot.exact_head}:{snapshot.observed_at}",
        "event_class": "RECONCILIATION_HEAD_DELTA", "source": "reconciliation",
        "repository": snapshot.repository, "observed_at": snapshot.observed_at,
        "target_ref": "refs/heads/main", "target_identity": snapshot.exact_head,
        "payload": {"trusted_exact_head": snapshot.exact_head, "prior_exact_head": prior_snapshot.exact_head},
        "idempotency_key": f"reconcile-head:{snapshot.exact_head}", "priority_hint": int(Priority.P1_EXACT_HEAD_REVIEW),
    })
    self._trace(event, "RECONCILIATION_DERIVED")
    if not self.connection.execute("SELECT 1 FROM events WHERE semantic_key=?", (event.semantic_key,)).fetchone():
        self.connection.execute(
            "INSERT INTO events(semantic_key,event_json,priority,adjudication_generation,state) VALUES (?,?,?,?, 'PENDING')",
            (event.semantic_key, _event_to_json(event), int(Priority.P1_EXACT_HEAD_REVIEW), 0),
        )

def store__materialize_authoritative_p2(self, snapshot: ReconciliationSnapshot) -> None:
    for event_class in sorted({item.upper() for item in snapshot.active_p2_classes}):
        key = _reconciliation_p2_class_key(snapshot.repository, snapshot.route_id, event_class)
        if self.connection.execute("SELECT 1 FROM events WHERE semantic_key=?", (key,)).fetchone():
            continue
        event = NormalizedEvent(
            event_id=f"reconciliation-p2:{event_class}:{snapshot.observed_at}",
            event_class=event_class,
            source="reconciliation",
            repository=snapshot.repository,
            observed_at=snapshot.observed_at,
            target_ref="refs/route/current",
            target_identity=snapshot.route_id,
            payload_digest=digest({"authoritative_active_p2_class": event_class}),
            supplied_idempotency_key=f"reconciliation-p2:{event_class}",
            semantic_kind=event_class,
            semantic_key=key,
            priority_hint=Priority.P2_BLOCKER_OR_DRIFT,
            class_priority_hint=Priority.P2_BLOCKER_OR_DRIFT,
            risk_markers=(),
        )
        self._trace(event, "RECONCILIATION_DERIVED")
        self.connection.execute(
            "INSERT INTO events(semantic_key,event_json,priority,adjudication_generation,state) VALUES (?,?,?,?, 'PENDING')",
            (key, _event_to_json(event), int(Priority.P2_BLOCKER_OR_DRIFT), 0),
        )
    for key in sorted(set(snapshot.active_p2_event_keys)):
        if self.connection.execute("SELECT 1 FROM events WHERE semantic_key=?", (key,)).fetchone():
            continue
        event = NormalizedEvent(
            event_id=f"reconciliation-p2-key:{snapshot.observed_at}:{key[:12]}",
            event_class="ACTIVE_BLOCKER",
            source="reconciliation",
            repository=snapshot.repository,
            observed_at=snapshot.observed_at,
            target_ref="refs/route/current",
            target_identity=snapshot.route_id,
            payload_digest=digest({"authoritative_active_p2_key": key}),
            supplied_idempotency_key=f"reconciliation-p2-key:{key}",
            semantic_kind="ACTIVE_BLOCKER",
            semantic_key=key,
            priority_hint=Priority.P2_BLOCKER_OR_DRIFT,
            class_priority_hint=Priority.P2_BLOCKER_OR_DRIFT,
            risk_markers=(),
        )
        self._trace(event, "RECONCILIATION_DERIVED")
        self.connection.execute(
            "INSERT INTO events(semantic_key,event_json,priority,adjudication_generation,state) VALUES (?,?,?,?, 'PENDING')",
            (key, _event_to_json(event), int(Priority.P2_BLOCKER_OR_DRIFT), 0),
        )

