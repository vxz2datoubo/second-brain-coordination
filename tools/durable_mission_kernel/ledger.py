"""B2 — Single-controller SQLite mission ledger.

Provides transactional, monotonic event/state persistence with checkpoint/replay
and consistent backup/recovery. All state mutations go through a single writer
(single-controller), and every mutation is committed atomically.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from . import canonical, reducers, schemas, verifier
from .schemas import EventType, MissionState


_SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    mission_id     TEXT PRIMARY KEY,
    run_id         TEXT NOT NULL,
    state          TEXT NOT NULL,
    state_seq      INTEGER NOT NULL,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    mission_id           TEXT NOT NULL,
    state_seq            INTEGER NOT NULL,
    event_type           TEXT NOT NULL,
    previous_event_hash  TEXT NOT NULL,
    event_hash           TEXT NOT NULL,
    canonical_bytes      BLOB NOT NULL,
    actor                TEXT NOT NULL,
    timestamp_iso        TEXT NOT NULL,
    payload_json         TEXT NOT NULL,
    digests_json         TEXT NOT NULL,
    PRIMARY KEY (mission_id, state_seq)
);

CREATE TABLE IF NOT EXISTS checkpoints (
    mission_id     TEXT NOT NULL,
    state_seq      INTEGER NOT NULL,
    snapshot_json  TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    PRIMARY KEY (mission_id, state_seq)
);

CREATE TABLE IF NOT EXISTS effects (
    effect_id        TEXT PRIMARY KEY,
    mission_id       TEXT NOT NULL,
    idempotency_key  TEXT NOT NULL,
    status           TEXT NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    executed_at      TEXT,
    outcome_json     TEXT,
    UNIQUE (mission_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS leases (
    lease_id         TEXT PRIMARY KEY,
    mission_id       TEXT NOT NULL,
    executor_id      TEXT NOT NULL,
    collision_domain TEXT NOT NULL,
    status           TEXT NOT NULL,
    start_ts         INTEGER NOT NULL,
    expiry_ts        INTEGER NOT NULL,
    renewed_ts       INTEGER NOT NULL
);
"""


class LedgerError(RuntimeError):
    """Raised on any ledger integrity or concurrency failure (fail closed)."""


class MissionLedger:
    """A single-controller SQLite ledger for one durable mission."""

    def __init__(self, path: str | Path):
        self._path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        # Single-controller => DELETE journal (fully ACID, no -wal/-shm locking
        # artifacts on Windows). WAL is for multi-reader concurrency, which the
        # single-writer kernel does not need.
        self._conn.execute("PRAGMA journal_mode=DELETE")
        self._conn.execute("PRAGMA foreign_keys=ON")
        with self._conn:
            self._conn.executescript(_SCHEMA)

    # -- basic helpers ------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def __enter__(self) -> "MissionLedger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- mission lifecycle ---------------------------------------------------
    def create_mission(self, mission_id: str, run_id: str, timestamp_iso: str,
                       actor: str = "WORKBUDDY_ENGINEERING_EXECUTOR") -> None:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT 1 FROM missions WHERE mission_id=?", (mission_id,)
            )
            if cur.fetchone() is not None:
                raise LedgerError(f"mission already exists: {mission_id}")
            genesis = verifier.build_genesis_event(
                mission_id=mission_id, run_id=run_id, actor=actor,
                timestamp_iso=timestamp_iso,
            )
            self._conn.execute(
                "INSERT INTO missions(mission_id, run_id, state, state_seq, created_at, updated_at)"
                " VALUES(?,?,?,?,?,?)",
                (mission_id, run_id, MissionState.CREATED.value, 0, timestamp_iso, timestamp_iso),
            )
            self._append_event_locked(genesis)

    def append_event(self, *, mission_id: str, event_type: str, actor: str,
                     timestamp_iso: str, payload: Any = None,
                     digests: dict | None = None) -> dict[str, Any]:
        """Append a single event, atomically advancing state via the reducer.

        Returns the stored event record (including its computed hash).
        """
        payload = {} if payload is None else payload
        digests = {} if digests is None else digests
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT run_id, state, state_seq FROM missions WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
            if row is None:
                raise LedgerError(f"unknown mission: {mission_id}")
            run_id, current_state, current_seq = row

            try:
                next_state = reducers.reduce_state(current_state, event_type)
            except reducers.ReducerError as e:
                raise LedgerError(f"illegal transition: {e}") from e
            new_seq = current_seq + 1

            prev_hash = self._head_hash_locked(mission_id)
            ev_hash = canonical.event_hash(
                prev_hash,
                mission_id=mission_id,
                run_id=run_id,
                state_seq=new_seq,
                event_type=event_type,
                actor=actor,
                timestamp_iso=timestamp_iso,
                payload=payload,
                digests=digests,
            )
            event = {
                "mission_id": mission_id,
                "run_id": run_id,
                "state_seq": new_seq,
                "event_type": event_type,
                "previous_event_hash": prev_hash,
                "event_hash": ev_hash,
                "actor": actor,
                "timestamp_iso": timestamp_iso,
                "payload": payload,
                "digests": digests,
            }
            self._conn.execute(
                "UPDATE missions SET state=?, state_seq=?, updated_at=? WHERE mission_id=?",
                (next_state, new_seq, timestamp_iso, mission_id),
            )
            self._append_event_locked(event)
            return event

    def _append_event_locked(self, event: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO events(mission_id, state_seq, event_type, previous_event_hash,"
            " event_hash, canonical_bytes, actor, timestamp_iso, payload_json, digests_json)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                event["mission_id"],
                event["state_seq"],
                event["event_type"],
                event["previous_event_hash"],
                event["event_hash"],
                canonical.jcs_bytes(event),
                event["actor"],
                event["timestamp_iso"],
                json.dumps(event["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                json.dumps(event["digests"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            ),
        )

    def _head_hash_locked(self, mission_id: str) -> str:
        row = self._conn.execute(
            "SELECT event_hash FROM events WHERE mission_id=? ORDER BY state_seq DESC LIMIT 1",
            (mission_id,),
        ).fetchone()
        if row is None:
            return canonical.GENESIS_PREVIOUS_HASH
        return row[0]

    # -- read / verify ------------------------------------------------------
    def read_events(self, mission_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT canonical_bytes FROM events WHERE mission_id=? ORDER BY state_seq",
                (mission_id,),
            ).fetchall()
        events = []
        for r in rows:
            events.append(json.loads(r[0].decode("utf-8")))
        return events

    def verify_chain(self, mission_id: str) -> bool:
        return verifier.verify_event_chain(self.read_events(mission_id))

    def current_state(self, mission_id: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT state FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
        if row is None:
            raise LedgerError(f"unknown mission: {mission_id}")
        return row[0]

    def current_state_seq(self, mission_id: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT state_seq FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
        if row is None:
            raise LedgerError(f"unknown mission: {mission_id}")
        return row[0]

    # -- checkpoint / replay -------------------------------------------------
    def checkpoint(self, mission_id: str, snapshot: dict[str, Any], timestamp_iso: str) -> None:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT state_seq FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            if row is None:
                raise LedgerError(f"unknown mission: {mission_id}")
            self._conn.execute(
                "INSERT INTO checkpoints(mission_id, state_seq, snapshot_json, created_at)"
                " VALUES(?,?,?,?)",
                (mission_id, row[0], json.dumps(snapshot, sort_keys=True, separators=(",", ":")), timestamp_iso),
            )

    def replay_state(self, mission_id: str) -> dict[str, Any]:
        """Reconstruct a mission's state by replaying its event chain.

        External effects are NOT reissued here — they are reconciled separately via
        the effects ledger (B3). This method returns the recomputed aggregate state.
        """
        events = self.read_events(mission_id)
        verifier.verify_event_chain(events)
        state = MissionState.CREATED.value
        payload_agg: dict[str, Any] = {"event_count": 0, "last_event_type": None}
        for ev in events:
            state = reducers.reduce_state(state, ev["event_type"])
            payload_agg["event_count"] += 1
            payload_agg["last_event_type"] = ev["event_type"]
        return {"state": state, "state_seq": len(events) - 1, "aggregate": payload_agg}

    # -- backup / recovery ---------------------------------------------------
    def backup(self, dest: str | Path) -> str:
        """Create a consistent online backup via SQLite's backup API."""
        dest = str(dest)
        with self._lock:
            target = sqlite3.connect(dest)
            try:
                self._conn.backup(target)
            finally:
                target.close()
        return dest

    @classmethod
    def recover_from_backup(cls, backup_path: str | Path, dest: str | Path) -> "MissionLedger":
        """Restore a ledger from a consistent backup into a fresh file."""
        backup_path, dest = str(backup_path), str(dest)
        src = sqlite3.connect(backup_path)
        try:
            tgt = sqlite3.connect(dest)
            try:
                src.backup(tgt)
            finally:
                tgt.close()
        finally:
            src.close()
        return cls(dest)

    def integrity_check(self) -> bool:
        with self._lock:
            row = self._conn.execute("PRAGMA integrity_check").fetchone()
        return row is not None and row[0] == "ok"


# Re-exported for convenience by dependent modules.
__all__ = ["MissionLedger", "LedgerError"]
