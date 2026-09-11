"""Durable synthetic Host Execution Broker candidate.

The broker is a host-local runtime extension of the existing Control Tower. It stores
host-local admission/lease evidence in SQLite and uses ``BEGIN IMMEDIATE`` so
concurrent clients cannot all observe a free resource and then race to start.
R1 never launches or terminates real processes.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from hashlib import sha256
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Mapping

from coordination.EXECUTION import canonical_write_paths as write_paths

from .models import (
    AdmissionDecision,
    AuthorityState,
    DecisionOutcome,
    EpisodeBudgetDecision,
    EpisodeBudgetOutcome,
    ExecutionRequest,
    LeaseBinding,
    ProcessStartReceipt,
    ResourceClaim,
    ResourceMode,
    ResourceType,
    TransportState,
    WorkerIdentity,
)

ACTIVE_EXECUTION_STATES = frozenset({"ADMITTED", "RUNNING", "CHECKPOINTING", "RESUMING"})
ACTIVE_LEASE_STATE = "ACTIVE"

ALWAYS_EXCLUSIVE = frozenset({
    ResourceType.RDC_PROCESS_MUTATION_CHANNEL,
    ResourceType.WORKBUDDY_DAEMON,
    ResourceType.WORKBUDDY_AGENT_SESSION,
    ResourceType.WORKBUDDY_ONE_TIME_RUNNER,
    ResourceType.CODEX_SESSION,
    ResourceType.LOCAL_PORT,
    ResourceType.EXCLUSIVE_LOCAL_RUNTIME,
})
READ_SHAREABLE = frozenset({
    ResourceType.HOST,
    ResourceType.BRANCH,
    ResourceType.WORKTREE,
    ResourceType.COLLISION_DOMAIN,
    ResourceType.WRITE_SURFACE,
    ResourceType.MARKET_DATA_PROVIDER,
})
DEFAULT_CAPACITY: Mapping[ResourceType, int] = {
    ResourceType.CPU_LIGHT: 8,
    ResourceType.CPU_HEAVY: 2,
    ResourceType.GPU_LOCAL: 1,
}


class BrokerError(RuntimeError):
    pass


class FencingError(BrokerError):
    pass


class ProcessOwnershipError(BrokerError):
    pass


def _write_surfaces_overlap(left: str, right: str) -> bool:
    lroot, ltree = write_paths.parse_write_pattern(left)
    rroot, rtree = write_paths.parse_write_pattern(right)
    if lroot == rroot:
        return True
    if rroot.startswith(lroot + "/"):
        return True
    if lroot.startswith(rroot + "/"):
        return True
    return False


class HostExecutionBroker:
    """SQLite-backed atomic host admission and durable lease projection."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        capacities: Mapping[ResourceType, int] | None = None,
        lease_ttl_ms: int = 30_000,
        clock=time.time,
    ) -> None:
        if lease_ttl_ms < 1:
            raise ValueError("lease_ttl_ms must be positive")
        self.db_path = str(db_path)
        if self.db_path == ":memory:":
            raise ValueError("durable Host Execution Broker requires file-backed SQLite")
        self._clock = clock
        self._lock = threading.RLock()
        self.lease_ttl_ms = lease_ttl_ms
        self.capacities = dict(DEFAULT_CAPACITY)
        if capacities:
            self.capacities.update(capacities)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=15, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=15000")
        if self.db_path != ":memory:":
            con.execute("PRAGMA journal_mode=WAL")
        return con

    @contextmanager
    def _connection(self):
        con = self._connect()
        try:
            yield con
        finally:
            con.close()

    def _now_ms(self) -> int:
        return int(self._clock() * 1000)

    def _init_db(self) -> None:
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    project_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    route_epoch INTEGER NOT NULL,
                    mission_id TEXT NOT NULL,
                    milestone_id TEXT NOT NULL,
                    episode_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    worktree TEXT NOT NULL,
                    collision_domain TEXT NOT NULL,
                    carrier TEXT NOT NULL,
                    model TEXT NOT NULL,
                    canonical_main_sha TEXT NOT NULL,
                    authority_receipt_digest TEXT NOT NULL,
                    authority_state TEXT NOT NULL,
                    repo_write INTEGER NOT NULL,
                    write_surfaces_json TEXT NOT NULL,
                    broker_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    terminal_state TEXT
                );
                CREATE TABLE IF NOT EXISTS resource_leases (
                    lease_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    units INTEGER NOT NULL,
                    generation INTEGER NOT NULL,
                    fencing_token TEXT NOT NULL,
                    status TEXT NOT NULL,
                    acquired_at_ms INTEGER NOT NULL,
                    expires_at_ms INTEGER NOT NULL,
                    released_at_ms INTEGER
                );
                CREATE INDEX IF NOT EXISTS ix_resource_active
                    ON resource_leases(resource_type, resource_id, status);
                CREATE TABLE IF NOT EXISTS process_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
                    payload_json TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_process_receipt_execution
                    ON process_receipts(execution_id);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL
                );
            """)

    def _event(
        self,
        con: sqlite3.Connection,
        execution_id: str | None,
        event_type: str,
        payload: Mapping[str, object],
    ) -> None:
        con.execute(
            "INSERT INTO events(execution_id,event_type,payload_json,created_at_ms) VALUES(?,?,?,?)",
            (
                execution_id,
                event_type,
                json.dumps(payload, sort_keys=True, default=str),
                self._now_ms(),
            ),
        )

    def _expire_stale_leases(self, con: sqlite3.Connection) -> None:
        now = self._now_ms()
        expired = list(
            con.execute(
                "SELECT DISTINCT execution_id FROM resource_leases "
                "WHERE status='ACTIVE' AND expires_at_ms<=?",
                (now,),
            )
        )
        if not expired:
            return
        con.execute(
            "UPDATE resource_leases SET status='FENCED', released_at_ms=? "
            "WHERE status='ACTIVE' AND expires_at_ms<=?",
            (now, now),
        )
        for row in expired:
            execution_id = str(row["execution_id"])
            remaining = con.execute(
                "SELECT COUNT(*) AS n FROM resource_leases "
                "WHERE execution_id=? AND status='ACTIVE'",
                (execution_id,),
            ).fetchone()["n"]
            if int(remaining) == 0:
                con.execute(
                    "UPDATE executions SET status='FENCED', terminal_state='LEASE_EXPIRED', "
                    "updated_at_ms=? WHERE execution_id=? AND status IN "
                    "('ADMITTED','RUNNING','CHECKPOINTING','RESUMING')",
                    (now, execution_id),
                )
                self._event(con, execution_id, "LEASES_EXPIRED_AND_FENCED", {})

    def _active_attempt_for_episode(
        self, con: sqlite3.Connection, request: ExecutionRequest
    ) -> sqlite3.Row | None:
        self._expire_stale_leases(con)
        return con.execute(
            """SELECT * FROM executions
               WHERE project_id=? AND task_id=? AND route_epoch=? AND episode_id=?
                 AND status IN ('ADMITTED','RUNNING','CHECKPOINTING','RESUMING')
               ORDER BY created_at_ms DESC LIMIT 1""",
            (request.project_id, request.task_id, request.route_epoch, request.episode_id),
        ).fetchone()

    def _active_leases(
        self, con: sqlite3.Connection, claim: ResourceClaim
    ) -> list[sqlite3.Row]:
        self._expire_stale_leases(con)
        if claim.resource_type == ResourceType.WRITE_SURFACE:
            candidates = list(
                con.execute(
                    """SELECT * FROM resource_leases
                       WHERE resource_type=? AND status='ACTIVE'""",
                    (claim.resource_type.value,),
                )
            )
            return [
                row for row in candidates
                if _write_surfaces_overlap(claim.resource_id, str(row["resource_id"]))
            ]
        return list(
            con.execute(
                """SELECT * FROM resource_leases
                   WHERE resource_type=? AND resource_id=? AND status='ACTIVE'""",
                (claim.resource_type.value, claim.resource_id),
            )
        )

    def _conflict_outcome(self, claim: ResourceClaim) -> DecisionOutcome:
        if claim.resource_type == ResourceType.WORKBUDDY_ONE_TIME_RUNNER:
            return DecisionOutcome.REROUTE
        if claim.resource_type in {
            ResourceType.CPU_LIGHT,
            ResourceType.CPU_HEAVY,
            ResourceType.GPU_LOCAL,
            ResourceType.MARKET_DATA_PROVIDER,
            ResourceType.RDC_PROCESS_MUTATION_CHANNEL,
        }:
            return DecisionOutcome.WAIT
        return DecisionOutcome.BLOCK_CONFLICT

    def _claim_compatible(
        self, claim: ResourceClaim, active: list[sqlite3.Row]
    ) -> tuple[bool, str]:
        if not active:
            return True, "free"
        if claim.exclusive or claim.resource_type in ALWAYS_EXCLUSIVE:
            return False, "exclusive resource already leased"
        if claim.resource_type in self.capacities:
            capacity = self.capacities[claim.resource_type]
            used = sum(int(row["units"]) for row in active)
            return (
                used + claim.units <= capacity,
                f"capacity {used}+{claim.units}/{capacity}",
            )
        if claim.resource_type in READ_SHAREABLE:
            if (
                claim.mode == ResourceMode.READ
                and all(row["mode"] == ResourceMode.READ.value for row in active)
            ):
                return True, "read/read compatible"
            return False, "mutable access conflicts with existing claim"
        return False, "unknown resource compatibility fails closed"

    def admit(self, request: ExecutionRequest) -> AdmissionDecision:
        """Atomically admit, join, queue, block, or reroute one execution request."""
        with self._lock, self._connection() as con:
            con.execute("BEGIN IMMEDIATE")
            self._expire_stale_leases(con)

            if request.authority_state != AuthorityState.CURRENT:
                self._event(
                    con,
                    None,
                    "ADMISSION_DENIED_STALE_AUTHORITY",
                    {
                        "task_id": request.task_id,
                        "authority_state": request.authority_state.value,
                    },
                )
                con.execute("COMMIT")
                return AdmissionDecision(
                    DecisionOutcome.BLOCK_CONFLICT,
                    None,
                    None,
                    f"authority is {request.authority_state.value}; fail closed",
                )

            duplicate = con.execute(
                "SELECT * FROM executions WHERE idempotency_key=?",
                (request.idempotency_key,),
            ).fetchone()
            if duplicate is not None:
                con.execute("COMMIT")
                state = str(duplicate["status"])
                return AdmissionDecision(
                    DecisionOutcome.JOIN_EXISTING,
                    str(duplicate["execution_id"]),
                    str(duplicate["broker_key"]),
                    f"idempotency key already materialized in state {state}; no second writer",
                    joined_execution_id=str(duplicate["execution_id"]),
                )

            prior = self._active_attempt_for_episode(con, request)
            if prior is not None:
                con.execute("COMMIT")
                return AdmissionDecision(
                    DecisionOutcome.WAIT,
                    None,
                    None,
                    "previous attempt for this task/route/episode is still active",
                    joined_execution_id=str(prior["execution_id"]),
                )

            claims = request.all_claims()
            for claim in claims:
                active = self._active_leases(con, claim)
                compatible, detail = self._claim_compatible(claim, active)
                if not compatible:
                    outcome = self._conflict_outcome(claim)
                    self._event(
                        con,
                        None,
                        "ADMISSION_DENIED",
                        {
                            "task_id": request.task_id,
                            "resource": claim.key,
                            "outcome": outcome.value,
                            "detail": detail,
                        },
                    )
                    con.execute("COMMIT")
                    return AdmissionDecision(
                        outcome, None, None, f"{claim.key}: {detail}"
                    )

            now = self._now_ms()
            execution_id = "EX-" + request.execution_identity[:24]
            broker_key = request.broker_key
            con.execute(
                """INSERT INTO executions(
                    execution_id,idempotency_key,project_id,task_id,route_epoch,
                    mission_id,milestone_id,episode_id,attempt,role,branch,worktree,
                    collision_domain,carrier,model,canonical_main_sha,
                    authority_receipt_digest,authority_state,repo_write,
                    write_surfaces_json,broker_key,status,created_at_ms,updated_at_ms
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    execution_id,
                    request.idempotency_key,
                    request.project_id,
                    request.task_id,
                    request.route_epoch,
                    request.mission_id,
                    request.milestone_id,
                    request.episode_id,
                    request.attempt,
                    request.role,
                    request.branch,
                    request.worktree,
                    request.collision_domain,
                    request.carrier,
                    request.model,
                    request.canonical_main_sha,
                    request.authority_receipt_digest,
                    request.authority_state.value,
                    int(request.repo_write),
                    json.dumps(list(request.write_surfaces), sort_keys=True),
                    broker_key,
                    "ADMITTED",
                    now,
                    now,
                ),
            )

            bindings: list[LeaseBinding] = []
            expires_at = now + self.lease_ttl_ms
            for claim in claims:
                last_gen = con.execute(
                    """SELECT COALESCE(MAX(generation),0) AS generation
                       FROM resource_leases WHERE resource_type=? AND resource_id=?""",
                    (claim.resource_type.value, claim.resource_id),
                ).fetchone()["generation"]
                generation = int(last_gen) + 1
                lease_seed = (
                    f"{execution_id}|{claim.key}|{generation}|{secrets.token_hex(16)}"
                )
                digest = sha256(lease_seed.encode("utf-8")).hexdigest()
                lease_id = "HL-" + digest[:24]
                fencing_token = "F-" + digest[24:56]
                con.execute(
                    """INSERT INTO resource_leases(
                        lease_id,execution_id,resource_type,resource_id,mode,units,
                        generation,fencing_token,status,acquired_at_ms,expires_at_ms
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        lease_id,
                        execution_id,
                        claim.resource_type.value,
                        claim.resource_id,
                        claim.mode.value,
                        claim.units,
                        generation,
                        fencing_token,
                        ACTIVE_LEASE_STATE,
                        now,
                        expires_at,
                    ),
                )
                bindings.append(
                    LeaseBinding(
                        lease_id=lease_id,
                        execution_id=execution_id,
                        holder=execution_id,
                        resource_type=claim.resource_type,
                        resource_id=claim.resource_id,
                        mode=claim.mode,
                        generation=generation,
                        fencing_token=fencing_token,
                        issued_at_ms=now,
                        expires_at_ms=expires_at,
                    )
                )

            self._event(
                con,
                execution_id,
                "ADMISSION_GRANTED",
                {
                    "broker_key": broker_key,
                    "resources": [binding.lease_id for binding in bindings],
                },
            )
            con.execute("COMMIT")
            return AdmissionDecision(
                DecisionOutcome.ADMIT,
                execution_id,
                broker_key,
                "atomic host admission committed",
                tuple(bindings),
            )

    def renew(self, binding: LeaseBinding) -> LeaseBinding:
        """Renew one current lease without changing generation/fencing identity."""
        with self._lock, self._connection() as con:
            con.execute("BEGIN IMMEDIATE")
            self._expire_stale_leases(con)
            row = con.execute(
                "SELECT * FROM resource_leases WHERE lease_id=?",
                (binding.lease_id,),
            ).fetchone()
            if row is None or row["status"] != ACTIVE_LEASE_STATE:
                con.execute("ROLLBACK")
                raise FencingError("STALE_EXECUTOR: lease is not active")
            if (
                int(row["generation"]) != binding.generation
                or row["fencing_token"] != binding.fencing_token
            ):
                con.execute("ROLLBACK")
                raise FencingError("STALE_EXECUTOR: lease generation/fencing mismatch")
            expires_at = self._now_ms() + self.lease_ttl_ms
            con.execute(
                "UPDATE resource_leases SET expires_at_ms=? WHERE lease_id=?",
                (expires_at, binding.lease_id),
            )
            self._event(
                con,
                binding.execution_id,
                "LEASE_RENEWED",
                {"lease_id": binding.lease_id, "expires_at_ms": expires_at},
            )
            con.execute("COMMIT")
            return LeaseBinding(
                lease_id=binding.lease_id,
                execution_id=binding.execution_id,
                holder=binding.holder,
                resource_type=binding.resource_type,
                resource_id=binding.resource_id,
                mode=binding.mode,
                generation=binding.generation,
                fencing_token=binding.fencing_token,
                issued_at_ms=binding.issued_at_ms,
                expires_at_ms=expires_at,
                state=ACTIVE_LEASE_STATE,
            )

    def assert_effect_authorized(self, binding: LeaseBinding) -> None:
        """Reject stale/superseded/expired lease generations before effects."""
        with self._connection() as con:
            con.execute("BEGIN IMMEDIATE")
            self._expire_stale_leases(con)
            row = con.execute(
                "SELECT * FROM resource_leases WHERE lease_id=?",
                (binding.lease_id,),
            ).fetchone()
            if row is None or row["status"] != ACTIVE_LEASE_STATE:
                con.execute("ROLLBACK")
                raise FencingError("STALE_EXECUTOR: lease is not active")
            if (
                str(row["execution_id"]) != binding.execution_id
                or int(row["generation"]) != binding.generation
                or row["fencing_token"] != binding.fencing_token
            ):
                con.execute("ROLLBACK")
                raise FencingError("STALE_EXECUTOR: lease identity/generation/fencing mismatch")
            newest = con.execute(
                """SELECT MAX(generation) AS generation FROM resource_leases
                   WHERE resource_type=? AND resource_id=?""",
                (binding.resource_type.value, binding.resource_id),
            ).fetchone()["generation"]
            if int(newest) != binding.generation:
                con.execute("ROLLBACK")
                raise FencingError("STALE_EXECUTOR: newer lease generation exists")
            con.execute("COMMIT")

    def release(self, execution_id: str, *, terminal_state: str = "COMPLETE") -> None:
        """Release resources but retain durable executions, lease history, and receipts."""
        with self._lock, self._connection() as con:
            con.execute("BEGIN IMMEDIATE")
            now = self._now_ms()
            changed = con.execute(
                """UPDATE executions SET status='TERMINAL', terminal_state=?, updated_at_ms=?
                   WHERE execution_id=? AND status IN ('ADMITTED','RUNNING','CHECKPOINTING','RESUMING')""",
                (terminal_state, now, execution_id),
            ).rowcount
            if changed != 1:
                con.execute("ROLLBACK")
                raise BrokerError("execution is not active or does not exist")
            con.execute(
                """UPDATE resource_leases SET status='RELEASED', released_at_ms=?
                   WHERE execution_id=? AND status='ACTIVE'""",
                (now, execution_id),
            )
            self._event(
                con,
                execution_id,
                "EXECUTION_RELEASED",
                {"terminal_state": terminal_state},
            )
            con.execute("COMMIT")

    def bind_process_start(
        self, execution_id: str, worker: WorkerIdentity
    ) -> ProcessStartReceipt:
        """Persist exact process identity for an already-admitted execution.

        This method never starts the process and is not canonical execution authority.
        """
        with self._lock, self._connection() as con:
            con.execute("BEGIN IMMEDIATE")
            self._expire_stale_leases(con)
            execution = con.execute(
                "SELECT * FROM executions WHERE execution_id=?", (execution_id,)
            ).fetchone()
            if execution is None or execution["status"] not in ACTIVE_EXECUTION_STATES:
                con.execute("ROLLBACK")
                raise ProcessOwnershipError("execution is not active")
            if (
                worker.task_id != execution["task_id"]
                or worker.route_epoch != execution["route_epoch"]
            ):
                con.execute("ROLLBACK")
                raise ProcessOwnershipError("worker task/route identity mismatch")
            lease = con.execute(
                "SELECT * FROM resource_leases WHERE lease_id=? AND execution_id=? AND status='ACTIVE'",
                (worker.execution_lease_id, execution_id),
            ).fetchone()
            if lease is None:
                con.execute("ROLLBACK")
                raise ProcessOwnershipError("worker lease is absent or inactive")
            if (
                int(lease["generation"]) != worker.generation
                or str(lease["fencing_token"]) != worker.fencing_token
            ):
                con.execute("ROLLBACK")
                raise ProcessOwnershipError("worker lease generation/fencing mismatch")

            receipt = ProcessStartReceipt(
                schema="PROCESS_START_RECEIPT/v1-candidate",
                execution_id=execution_id,
                broker_key=str(execution["broker_key"]),
                task_id=str(execution["task_id"]),
                route_epoch=int(execution["route_epoch"]),
                role=str(execution["role"]),
                branch=str(execution["branch"]),
                worktree=str(execution["worktree"]),
                collision_domain=str(execution["collision_domain"]),
                carrier=str(execution["carrier"]),
                model=str(execution["model"]),
                canonical_main_sha=str(execution["canonical_main_sha"]),
                worker=worker,
                issued_at_ms=self._now_ms(),
            )
            payload = json.dumps(asdict(receipt), sort_keys=True, default=str)
            existing = con.execute(
                "SELECT payload_json FROM process_receipts WHERE execution_id=? ORDER BY created_at_ms LIMIT 1",
                (execution_id,),
            ).fetchone()
            if existing is not None:
                prior = json.loads(str(existing["payload_json"]))
                current = json.loads(payload)
                prior.pop("issued_at_ms", None)
                current.pop("issued_at_ms", None)
                if prior != current:
                    con.execute("ROLLBACK")
                    raise ProcessOwnershipError(
                        "execution already bound to a different process identity"
                    )
                con.execute("COMMIT")
                return receipt

            receipt_id = "PSR-" + sha256(payload.encode("utf-8")).hexdigest()[:24]
            con.execute(
                "INSERT INTO process_receipts(receipt_id,execution_id,payload_json,created_at_ms) VALUES(?,?,?,?)",
                (receipt_id, execution_id, payload, receipt.issued_at_ms),
            )
            con.execute(
                "UPDATE executions SET status='RUNNING', updated_at_ms=? WHERE execution_id=?",
                (receipt.issued_at_ms, execution_id),
            )
            self._event(
                con, execution_id, "PROCESS_START_RECEIPT", {"receipt_id": receipt_id}
            )
            con.execute("COMMIT")
            return receipt

    @staticmethod
    def process_identity_matches(
        observed: WorkerIdentity, expected: WorkerIdentity
    ) -> bool:
        """Exact-match ownership predicate; PID alone is never enough."""
        return observed == expected

    @staticmethod
    def transport_state(
        *, transport_timed_out: bool, worker_alive: bool | None
    ) -> TransportState:
        if transport_timed_out:
            return TransportState.OUTCOME_UNKNOWN
        if worker_alive is False:
            return TransportState.WORKER_FAILURE
        return TransportState.OK

    @staticmethod
    def episode_budget(
        *,
        turns_used: int,
        max_turns: int,
        mission_complete: bool,
        checkpoint_ref: str | None,
    ) -> EpisodeBudgetDecision:
        if turns_used < 0 or max_turns < 1:
            raise ValueError("invalid episode budget")
        if mission_complete:
            return EpisodeBudgetDecision(
                EpisodeBudgetOutcome.MISSION_COMPLETE, False, False, checkpoint_ref
            )
        if turns_used < max_turns:
            return EpisodeBudgetDecision(
                EpisodeBudgetOutcome.CONTINUE_EPISODE, False, False, checkpoint_ref
            )
        if not checkpoint_ref:
            raise ValueError(
                "checkpoint_ref is required before rolling to a successor episode"
            )
        return EpisodeBudgetDecision(
            EpisodeBudgetOutcome.CHECKPOINT_AND_SUCCESSOR,
            True,
            True,
            checkpoint_ref,
        )

    def history(self, execution_id: str) -> dict[str, object]:
        """Return durable terminal/readback evidence after resource release."""
        with self._connection() as con:
            con.execute("BEGIN")
            execution = con.execute(
                "SELECT * FROM executions WHERE execution_id=?", (execution_id,)
            ).fetchone()
            leases = list(
                con.execute(
                    "SELECT * FROM resource_leases WHERE execution_id=? "
                    "ORDER BY resource_type,resource_id,generation",
                    (execution_id,),
                )
            )
            receipts = list(
                con.execute(
                    "SELECT * FROM process_receipts WHERE execution_id=? ORDER BY created_at_ms",
                    (execution_id,),
                )
            )
            events = list(
                con.execute(
                    "SELECT * FROM events WHERE execution_id=? ORDER BY seq",
                    (execution_id,),
                )
            )
            con.execute("COMMIT")
        return {
            "execution": dict(execution) if execution is not None else None,
            "leases": [dict(row) for row in leases],
            "receipts": [dict(row) for row in receipts],
            "events": [dict(row) for row in events],
        }
