from __future__ import annotations

from _iagl_contracts import *

def store_set_value(self, key: str, value: int) -> None:
    self.connection.execute("INSERT INTO accounting VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    self.connection.commit()

def store_save_checkpoint(self, checkpoint: Checkpoint) -> None:
    checkpoint.validate()
    self.connection.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?)", (checkpoint.checkpoint_id, json.dumps(asdict(checkpoint), sort_keys=True)))
    self.connection.commit()

def store_load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
    row = self.connection.execute("SELECT record FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)).fetchone()
    if not row:
        return None
    value = json.loads(row[0])
    for name in ("source_refs", "evidence_digests", "completed_atomic_steps", "open_unknowns", "resume_preconditions"):
        value[name] = tuple(value[name])
    checkpoint = Checkpoint(**value)
    checkpoint.validate()
    return checkpoint

def store_issue_retrieval_complete_empty(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant, observation: RetrievalProviderObservation) -> RetrievalCompletenessProof:
    current = self.current_snapshot()
    observation.validate()
    if not current or current[0] != grant or current[1] != snapshot:
        raise SupervisorError("RETRIEVAL_PROOF_ISSUANCE_REQUIRES_CURRENT_RECONCILIATION")
    if observation.repository != snapshot.repository or observation.exact_revision != snapshot.exact_head:
        raise SupervisorError("RETRIEVAL_PROVIDER_OBSERVATION_REVISION_MISMATCH")
    proof = RetrievalCompletenessProof(
        snapshot.repository, snapshot.exact_head, observation.request_digest, observation.authority_scope_ref,
        observation.evidence_ref, observation.observation_id, observation.observation_digest(),
        grant.identity, grant.generation, True, f"stage-a:{uuid.uuid4()}",
    )
    self.connection.execute("INSERT INTO retrieval_proofs VALUES (?,?,?,'ISSUED')", (proof.issuance_ref, proof.proof_digest(), observation.observation_digest()))
    self.connection.commit()
    return proof

def store_consume_retrieval_proof(self, proof: RetrievalCompletenessProof, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant, request_digest: str) -> bool:
    if not proof.structurally_matches(snapshot, grant, request_digest):
        return False
    cur = self.connection.execute(
        "UPDATE retrieval_proofs SET state='CONSUMED' WHERE issuance_ref=? AND proof_digest=? AND provider_observation_digest=? AND state='ISSUED'",
        (proof.issuance_ref, proof.proof_digest(), proof.provider_observation_digest),
    )
    self.connection.commit()
    return cur.rowcount == 1

def store__starvation_row(self, slice_id: str) -> tuple[int, int, str] | None:
    row = self.connection.execute("SELECT counter,last_seen_generation,last_reason FROM starvation WHERE slice_id=?", (slice_id,)).fetchone()
    return (int(row[0]), int(row[1]), str(row[2])) if row else None

def store_starvation_status(self, slice_: ImprovementSlice, generation: int) -> StarvationStatus:
    row = self._starvation_row(slice_.slice_id)
    counter = row[0] if row else 0
    last_seen = row[1] if row else -1
    aged = counter >= _STARVATION_THRESHOLD
    material = _normalized(slice_.materiality) == "material"
    fresh = last_seen < generation
    promoted = bool(aged and material and fresh and slice_.priority == Priority.P4_RESEARCH)
    effective = Priority.P3_BOUNDED_IMPROVEMENT if promoted else slice_.priority
    if aged and material and fresh:
        reason = "AGING+MATERIALITY+FRESH_RECONCILIATION:P4_TO_P3" if promoted else "AGING+MATERIALITY+FRESH_RECONCILIATION:P3_WITHIN_CLASS"
    elif aged and not material:
        reason = "AGING_PRESENT:MATERIALITY_REQUIRED"
    elif aged and not fresh:
        reason = "AGING_PRESENT:FRESH_RECONCILIATION_REQUIRED"
    else:
        reason = f"AGING_COUNTER:{counter}/{_STARVATION_THRESHOLD}"
    return StarvationStatus(slice_.slice_id, counter, slice_.priority, effective, aged, material, fresh, promoted, reason)

def store_starvation_visibility(self, candidates: Sequence[ImprovementSlice], generation: int) -> tuple[StarvationStatus, ...]:
    statuses = [self.starvation_status(item, generation) for item in candidates]
    return tuple(sorted((item for item in statuses if item.counter > 0), key=lambda item: item.slice_id))

def store_record_starvation_selection(self, candidates: Sequence[ImprovementSlice], selected_id: str, generation: int) -> None:
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
            "INSERT INTO starvation VALUES (?,?,?,?) ON CONFLICT(slice_id) DO UPDATE SET counter=excluded.counter,last_seen_generation=excluded.last_seen_generation,last_reason=excluded.last_reason",
            (item.slice_id, new_counter, generation, reason),
        )
    self.connection.commit()

