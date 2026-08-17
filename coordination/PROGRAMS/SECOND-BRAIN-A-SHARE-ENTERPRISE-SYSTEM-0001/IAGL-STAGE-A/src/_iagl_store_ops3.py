from __future__ import annotations

from _iagl_contracts import *

def store_create_review_work(self, event: NormalizedEvent, grant: ReconciliationGrant) -> ReviewWorkIdentity:
    work = ReviewWorkIdentity(event.semantic_key, event.target_identity, grant.identity, grant.generation)
    self.connection.execute(
        "INSERT OR IGNORE INTO review_work VALUES (?,?,?,?,?,'READY')",
        (work.key(), work.semantic_event_key, work.target_head, work.reconciliation_identity, work.reconciliation_generation),
    )
    self.connection.commit()
    return work

def store_head_is_reviewed(self, target_head: str) -> bool:
    return bool(self.connection.execute("SELECT 1 FROM reviewed_heads WHERE target_head=?", (target_head,)).fetchone())

def store_consume_review_work(self, work: ReviewWorkIdentity, grant: ReconciliationGrant) -> bool:
    cur = self.connection.execute(
        "UPDATE review_work SET state='CONSUMED' WHERE work_key=? AND semantic_key=? AND target_head=? AND identity=? AND generation=? AND state='READY'",
        (work.key(), work.semantic_event_key, work.target_head, grant.identity, grant.generation),
    )
    if cur.rowcount != 1:
        self.connection.rollback()
        return False
    self.connection.execute("UPDATE events SET state='CONSUMED' WHERE semantic_key=? AND state='PENDING'", (work.semantic_event_key,))
    self.connection.execute("INSERT OR REPLACE INTO reviewed_heads VALUES (?,?,?)", (work.target_head, work.key(), grant.generation))
    self.connection.commit()
    return True

def store_acquire_lease(self, slice_id: str, owner: str) -> LeaseGrant | None:
    self.connection.execute("BEGIN IMMEDIATE")
    try:
        row = self.connection.execute("SELECT generation,active FROM leases WHERE slice_id=?", (slice_id,)).fetchone()
        if row and row[1]:
            self.connection.execute("ROLLBACK")
            return None
        generation = (row[0] if row else 0) + 1
        token = str(uuid.uuid4())
        self.connection.execute(
            "INSERT INTO leases VALUES (?,?,?,?,1) ON CONFLICT(slice_id) DO UPDATE SET owner=excluded.owner,generation=excluded.generation,token=excluded.token,active=1",
            (slice_id, owner, generation, token),
        )
        self.connection.execute("COMMIT")
        return LeaseGrant(slice_id, owner, generation, token)
    except Exception:
        self.connection.execute("ROLLBACK")
        raise

def store__lease_matches(self, lease: LeaseGrant) -> bool:
    row = self.connection.execute("SELECT owner,generation,token,active FROM leases WHERE slice_id=?", (lease.slice_id,)).fetchone()
    return row == (lease.owner, lease.generation, lease.fencing_token, 1)

def store_execution_is_active(self, plan: ExecutionPlan, lease: LeaseGrant) -> bool:
    current = self.current_snapshot()
    plan_row = self.connection.execute("SELECT identity,generation,state FROM plans WHERE plan_id=?", (plan.plan_id,)).fetchone()
    return bool(plan.slice.slice_id == lease.slice_id and current and plan_row == (current[0].identity, current[0].generation, "EXECUTING") and self._lease_matches(lease))

def store_release_lease(self, grant: LeaseGrant) -> bool:
    cur = self.connection.execute("UPDATE leases SET active=0 WHERE slice_id=? AND owner=? AND generation=? AND token=? AND active=1", (grant.slice_id, grant.owner, grant.generation, grant.fencing_token))
    self.connection.commit()
    return cur.rowcount == 1

def store_create_plan(self, grant: ReconciliationGrant, slice_: ImprovementSlice) -> ExecutionPlan:
    plan_id = digest({"snapshot": grant.identity, "generation": grant.generation, "slice": _slice_to_json(slice_)})
    self.connection.execute("INSERT OR REPLACE INTO plans VALUES (?,?,?,?,?)", (plan_id, grant.identity, grant.generation, _slice_to_json(slice_), "READY"))
    self.connection.commit()
    return ExecutionPlan(plan_id, grant, slice_)

def store_checkpointed_slice(self, checkpoint: Checkpoint) -> ImprovementSlice | None:
    row = self.connection.execute("SELECT slice_json FROM plans WHERE plan_id=? AND identity=? AND generation=?", (checkpoint.plan_id, checkpoint.snapshot_identity, checkpoint.reconciliation_generation)).fetchone()
    if not row:
        return None
    slice_ = _slice_from_json(row[0])
    if slice_.slice_id != checkpoint.slice_id or _slice_digest(slice_) != checkpoint.slice_digest:
        return None
    return slice_

def store_authorize_execution(self, plan: ExecutionPlan, lease: LeaseGrant, budget_limit: int) -> tuple[ImprovementSlice, ReconciliationSnapshot] | None:
    self.connection.execute("BEGIN IMMEDIATE")
    try:
        current = self.current_snapshot()
        plan_row = self.connection.execute("SELECT identity,generation,slice_json,state FROM plans WHERE plan_id=?", (plan.plan_id,)).fetchone()
        lease_row = self.connection.execute("SELECT owner,generation,token,active FROM leases WHERE slice_id=?", (lease.slice_id,)).fetchone()
        if not current or not plan_row or plan_row[3] != "READY" or not lease_row:
            self.connection.execute("ROLLBACK")
            return None
        current_grant, snapshot = current
        slice_ = _slice_from_json(plan_row[2])
        used = self.value("budget_used")
        try:
            slice_.validate(snapshot)
        except SupervisorError:
            self.connection.execute("ROLLBACK")
            return None
        valid = (
            plan.slice.slice_id == lease.slice_id and slice_.slice_id == lease.slice_id
            and _slice_digest(plan.slice) == _slice_digest(slice_)
            and plan_row[0] == current_grant.identity == plan.snapshot.identity
            and plan_row[1] == current_grant.generation == plan.snapshot.generation
            and lease_row == (lease.owner, lease.generation, lease.fencing_token, 1)
            and snapshot.governance_mode == GovernanceMode.AUTONOMOUS and not snapshot.pending_p0
            and used + slice_.estimated_cost <= budget_limit
        )
        if not valid:
            self.connection.execute("ROLLBACK")
            return None
        self.connection.execute("UPDATE plans SET state='EXECUTING' WHERE plan_id=?", (plan.plan_id,))
        self.connection.execute("INSERT INTO accounting VALUES ('budget_used',?) ON CONFLICT(key) DO UPDATE SET value=value+excluded.value", (slice_.estimated_cost,))
        self.connection.execute("COMMIT")
        return slice_, snapshot
    except Exception:
        self.connection.execute("ROLLBACK")
        raise

def store_value(self, key: str) -> int:
    row = self.connection.execute("SELECT value FROM accounting WHERE key=?", (key,)).fetchone()
    return int(row[0]) if row else 0
