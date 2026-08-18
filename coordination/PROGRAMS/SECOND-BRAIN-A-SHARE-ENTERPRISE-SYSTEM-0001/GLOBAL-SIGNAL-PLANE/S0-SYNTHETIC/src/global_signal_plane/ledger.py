"""SQLite-backed append-only ledger, durable CAS projection, and S0C guards."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .models import SignalEvent, SignalLink, SignalPlaneError


REDUCER_VERSION = "S0C-3"
_OPERATIONAL_SIGNAL_KINDS = frozenset({"STATUS", "REVOCATION"})
_LIFECYCLE_EVENT_TYPES = frozenset({"SIGNAL_CLOSURE_ASSESSMENT", "EXPLICIT_SIGNAL_REVOKE"})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _checksum(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass
class AuthorityBoundary:
    """Observed S0C capability state; denied attempts never mutate another authority."""

    execution_authorized: bool = False
    w3_mutated: bool = False
    domain_written: bool = False
    guard_codes: list[str] = field(default_factory=list)

    def deny(self, code: str) -> dict[str, Any]:
        self.guard_codes.append(code)
        return {"allowed": False, "code": code}

    def snapshot(self) -> dict[str, Any]:
        return {
            "execution_authorized": self.execution_authorized,
            "w3_mutated": self.w3_mutated,
            "domain_written": self.domain_written,
            "guard_codes": sorted(set(self.guard_codes)),
        }


class DurableSignalLedger:
    """Public-safe local history. Input revision and projection CAS are both durable."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.connection = sqlite3.connect(self.db_path, timeout=5.0)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS admitted_events (
              ledger_offset INTEGER PRIMARY KEY AUTOINCREMENT, event_source TEXT NOT NULL, event_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL, semantic_hash TEXT NOT NULL, record_json TEXT NOT NULL,
              UNIQUE(event_source, event_id), UNIQUE(idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS signal_links (
              link_id TEXT PRIMARY KEY, record_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ledger_meta (
              singleton INTEGER PRIMARY KEY CHECK(singleton = 1), input_revision INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projection_meta (
              singleton INTEGER PRIMARY KEY CHECK(singleton = 1), projection_version INTEGER NOT NULL,
              input_revision INTEGER NOT NULL DEFAULT 0, checksum TEXT NOT NULL, projection_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rejected_events (
              reject_id INTEGER PRIMARY KEY AUTOINCREMENT, reason_code TEXT NOT NULL, path TEXT NOT NULL,
              payload_fingerprint TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS deferred_events (
              deferred_id INTEGER PRIMARY KEY AUTOINCREMENT, idempotency_key TEXT NOT NULL UNIQUE,
              semantic_hash TEXT NOT NULL, reason_code TEXT NOT NULL, record_json TEXT NOT NULL
            );
        """)
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(projection_meta)")}
        if "input_revision" not in columns:
            self.connection.execute("ALTER TABLE projection_meta ADD COLUMN input_revision INTEGER NOT NULL DEFAULT 0")
        self.connection.execute("INSERT OR IGNORE INTO ledger_meta(singleton, input_revision) VALUES(1, 0)")
        self.connection.commit()
        self.boundary = AuthorityBoundary()

    def close(self) -> None:
        self.connection.close()

    def _begin(self) -> None:
        self.connection.execute("BEGIN IMMEDIATE")

    def _rollback(self) -> None:
        if self.connection.in_transaction:
            self.connection.rollback()

    def _bump_input_revision(self) -> int:
        self.connection.execute("UPDATE ledger_meta SET input_revision = input_revision + 1 WHERE singleton = 1")
        return self.input_revision()

    def input_revision(self) -> int:
        row = self.connection.execute("SELECT input_revision FROM ledger_meta WHERE singleton = 1").fetchone()
        return int(row["input_revision"])

    @staticmethod
    def _is_material(snapshot: Mapping[str, Any]) -> bool:
        return snapshot.get("signal_kind") in {"RISK", "BLOCKER", "INCIDENT"}

    def ingest_raw(self, payload: Mapping[str, Any], *, update_projection: bool = True,
                   capacity_limit: int | None = None) -> dict[str, Any]:
        try:
            event = SignalEvent.from_dict(payload)
        except SignalPlaneError as exc:
            fingerprint = _checksum(payload if isinstance(payload, Mapping) else {"not_object": True})
            with self.connection:
                self.connection.execute(
                    "INSERT INTO rejected_events(reason_code, path, payload_fingerprint) VALUES (?, ?, ?)",
                    (exc.code, exc.path, fingerprint),
                )
            return {"status": "REJECTED", "code": exc.code, "path": exc.path, "quarantined": True}
        return self.ingest(event, update_projection=update_projection, capacity_limit=capacity_limit)

    def ingest(self, event: SignalEvent, *, update_projection: bool = True,
               capacity_limit: int | None = None) -> dict[str, Any]:
        """Atomically enforce idempotency identity and bounded deferral before one append."""
        snapshot, semantic_hash, key = event.as_dict(), event.semantic_hash, event.idempotency_key
        try:
            self._begin()
            same_key = self.connection.execute(
                "SELECT ledger_offset, semantic_hash FROM admitted_events WHERE idempotency_key = ?", (key,)
            ).fetchone()
            if same_key:
                if same_key["semantic_hash"] != semantic_hash:
                    raise SignalPlaneError("IDEMPOTENCY_KEY_COLLISION", "/idempotency_key", "same idempotency key carries different semantic content")
                self.connection.commit()
                return {"status": "IDEMPOTENT_DUPLICATE", "receipt_offset": same_key["ledger_offset"], "effective_state_changed": False}
            same_event = self.connection.execute(
                "SELECT ledger_offset, semantic_hash FROM admitted_events WHERE event_source = ? AND event_id = ?",
                (snapshot["event_source"], snapshot["event_id"]),
            ).fetchone()
            if same_event:
                if same_event["semantic_hash"] != semantic_hash:
                    raise SignalPlaneError("EVENT_ID_COLLISION", "/event_id", "same source and event id carry different semantic content")
                self.connection.commit()
                return {"status": "IDEMPOTENT_DUPLICATE", "receipt_offset": same_event["ledger_offset"], "effective_state_changed": False}
            if capacity_limit is not None and capacity_limit >= 0:
                admitted = int(self.connection.execute("SELECT count(*) FROM admitted_events").fetchone()[0])
                if admitted >= capacity_limit and not self._is_material(snapshot):
                    existing_deferred = self.connection.execute(
                        "SELECT deferred_id, semantic_hash FROM deferred_events WHERE idempotency_key = ?", (key,)
                    ).fetchone()
                    if existing_deferred:
                        if existing_deferred["semantic_hash"] != semantic_hash:
                            raise SignalPlaneError("IDEMPOTENCY_KEY_COLLISION", "/idempotency_key", "deferred key carries different semantic content")
                        self.connection.commit()
                        return {"status": "IDEMPOTENT_DUPLICATE", "receipt_offset": existing_deferred["deferred_id"], "effective_state_changed": False}
                    self.connection.execute(
                        "INSERT INTO deferred_events(idempotency_key, semantic_hash, reason_code, record_json) VALUES (?, ?, ?, ?)",
                        (key, semantic_hash, "BACKPRESSURE_DEFERRED", _canonical(snapshot)),
                    )
                    self.connection.commit()
                    return {"status": "DEFERRED_BACKPRESSURE", "code": "BACKPRESSURE_DEFERRED", "effective_state_changed": False}
            cursor = self.connection.execute(
                "INSERT INTO admitted_events(event_source,event_id,idempotency_key,semantic_hash,record_json) VALUES (?, ?, ?, ?, ?)",
                (snapshot["event_source"], snapshot["event_id"], key, semantic_hash, _canonical(snapshot)),
            )
            offset = cursor.lastrowid
            revision = self._bump_input_revision()
            self.connection.commit()
        except SignalPlaneError:
            self._rollback()
            raise
        except sqlite3.IntegrityError as exc:
            self._rollback()
            raise SignalPlaneError("DURABLE_IDEMPOTENCY_CONSTRAINT", "/idempotency_key", "durable uniqueness constraint rejected append") from exc
        if update_projection:
            self._rebuild_after_input()
        return {"status": "ADMITTED", "receipt_offset": offset, "input_revision": revision, "effective_state_changed": True}

    def append_link(self, link: SignalLink, *, update_projection: bool = True) -> dict[str, Any]:
        encoded = _canonical(link.as_dict())
        try:
            self._begin()
            existing = self.connection.execute("SELECT record_json FROM signal_links WHERE link_id = ?", (link.link_id,)).fetchone()
            if existing:
                if existing["record_json"] != encoded:
                    raise SignalPlaneError("LINK_ID_COLLISION", "/link_id", "link ids are immutable")
                self.connection.commit()
                return {"status": "IDEMPOTENT_DUPLICATE", "effective_state_changed": False}
            self.connection.execute("INSERT INTO signal_links(link_id, record_json) VALUES (?, ?)", (link.link_id, encoded))
            revision = self._bump_input_revision()
            self.connection.commit()
        except SignalPlaneError:
            self._rollback()
            raise
        if update_projection:
            self._rebuild_after_input()
        return {"status": "ADMITTED", "input_revision": revision, "effective_state_changed": True}

    def _rebuild_after_input(self) -> dict[str, Any]:
        for _ in range(3):
            try:
                return self.rebuild_projection(expected_version=self.current_projection_version())
            except SignalPlaneError as exc:
                if exc.code != "STALE_PROJECTION_VERSION":
                    raise
        raise SignalPlaneError("STALE_PROJECTION_VERSION", "/expected_projection_version", "bounded projection recovery exhausted")

    def history(self) -> list[dict[str, Any]]:
        return [json.loads(row["record_json"]) | {"ledger_offset": row["ledger_offset"]} for row in self.connection.execute("SELECT ledger_offset, record_json FROM admitted_events ORDER BY ledger_offset")]

    def rejected_count(self) -> int:
        return int(self.connection.execute("SELECT count(*) FROM rejected_events").fetchone()[0])

    def backpressure_state(self, capacity_limit: int) -> dict[str, int | bool]:
        admitted = int(self.connection.execute("SELECT count(*) FROM admitted_events").fetchone()[0])
        deferred = int(self.connection.execute("SELECT count(*) FROM deferred_events").fetchone()[0])
        return {"capacity_limit": capacity_limit, "admitted": admitted, "deferred": deferred, "pressure_active": admitted >= capacity_limit}

    def current_projection_version(self) -> int:
        row = self.connection.execute("SELECT projection_version FROM projection_meta WHERE singleton = 1").fetchone()
        return int(row["projection_version"]) if row else 0

    def current_projection(self) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT projection_version, projection_json FROM projection_meta WHERE singleton = 1").fetchone()
        if row is None:
            return None
        projection = json.loads(row["projection_json"])
        if projection.get("reducer_version") != REDUCER_VERSION:
            return self.rebuild_projection(expected_version=int(row["projection_version"]))
        return projection

    def attempt_merge(self, left: SignalEvent, right: SignalEvent) -> dict[str, Any]:
        """No automatic cluster merge: incompatible domain/authority/touch needs review."""
        left_data, right_data = left.as_dict(), right.as_dict()
        incompatible = any((
            left_data["primary_domain"] != right_data["primary_domain"],
            sorted(left_data["authority_targets"]) != sorted(right_data["authority_targets"]),
            sorted(left_data["touch_set"]) != sorted(right_data["touch_set"]),
        ))
        if incompatible:
            return self.boundary.deny("SEMANTIC_FALSE_MERGE_BLOCKED")
        return self.boundary.deny("MERGE_REVIEW_REQUIRED")

    def attempt_execution_authorization(self, event: SignalEvent) -> dict[str, Any]:
        del event
        return self.boundary.deny("MISSING_EXECUTION_AUTHORIZATION")

    def attempt_w3_write(self, event: SignalEvent) -> dict[str, Any]:
        del event
        return self.boundary.deny("KNOWLEDGE_CANDIDATE_REF_ONLY")

    def attempt_domain_write(self, event: SignalEvent) -> dict[str, Any]:
        del event
        return self.boundary.deny("DOMAIN_ADAPTER_REQUIRED")

    def attempt_cross_domain_promotion(self, event: SignalEvent) -> dict[str, Any]:
        if not event.as_dict()["cross_domain_candidate"]:
            return self.boundary.deny("CROSS_DOMAIN_CANDIDATE_REQUIRED")
        return self.boundary.deny("CROSS_DOMAIN_TEST_REQUIRED")

    def authority_observation(self) -> dict[str, Any]:
        return self.boundary.snapshot()

    @staticmethod
    def _is_semantic_origin(event: Mapping[str, Any]) -> bool:
        return event.get("event_type") not in _LIFECYCLE_EVENT_TYPES and event.get("signal_kind") not in _OPERATIONAL_SIGNAL_KINDS

    def _reduce(self) -> dict[str, Any]:
        history = self.history()
        semantic_origin: dict[str, str] = {}
        semantic_conflicts: set[str] = set()
        for event in history:
            if not self._is_semantic_origin(event):
                continue
            key, kind = event["signal_id"], str(event["signal_kind"])
            prior = semantic_origin.get(key)
            if prior is None:
                semantic_origin[key] = kind
            elif prior != kind:
                semantic_conflicts.add(key)

        signals: dict[str, dict[str, Any]] = {}
        ranks = {"NOT_STARTED": 0, "AUTHORIZED": 1, "EXECUTING": 2, "REVIEW": 3, "DONE": 4, "BLOCKED": 4, "CANCELLED": 5}
        for event in history:
            key = event["signal_id"]
            order = event.get("source_sequence") if event.get("source_sequence") is not None else event["ledger_offset"]
            current = signals.get(key)
            current_order = current.get("source_order", -1) if current else -1
            if order < current_order:
                continue
            if current and ranks[event["execution_state"]] < ranks[current["execution_state"]] and event["execution_state"] not in {"CANCELLED", "BLOCKED"}:
                continue
            signals[key] = {
                "signal_id": key,
                "signal_kind": semantic_origin.get(key, str(event["signal_kind"])),
                "planning_state": event["planning_state"],
                "execution_state": event["execution_state"],
                "epistemic_state": event["epistemic_state"],
                "source_order": order,
                "provenance_event_refs": sorted(set((current or {}).get("provenance_event_refs", []) + [event["event_id"]])),
            }
            for target in event["revokes_refs"]:
                if target in signals:
                    signals[target]["planning_state"] = "SUPERSEDED"
                    signals[target]["execution_state"] = "CANCELLED"

        for key in semantic_conflicts:
            if key in signals:
                signals[key]["planning_state"] = "CONFLICTED"
                signals[key]["epistemic_state"] = "NEEDS_REVALIDATION"

        links = [json.loads(row["record_json"]) for row in self.connection.execute("SELECT record_json FROM signal_links ORDER BY link_id")]
        return {
            "reducer_version": REDUCER_VERSION,
            "ledger_watermark": len(history),
            "input_revision": self.input_revision(),
            "signals": [signals[key] for key in sorted(signals)],
            "links": links,
            "clusters": [],
            "views": self._views(signals),
        }

    @staticmethod
    def _views(signals: Mapping[str, Mapping[str, Any]]) -> dict[str, list[str]]:
        result = {name: [] for name in ("OPEN", "BLOCKED", "SUPERSEDED", "CLOSED_NO_ACTION", "NEEDS_REVALIDATION")}
        for signal_id, state in signals.items():
            if state["planning_state"] == "SUPERSEDED":
                result["SUPERSEDED"].append(signal_id)
            elif state["execution_state"] == "BLOCKED":
                result["BLOCKED"].append(signal_id)
            elif state["planning_state"] == "CLOSED_NO_ACTION":
                result["CLOSED_NO_ACTION"].append(signal_id)
            elif state["epistemic_state"] == "NEEDS_REVALIDATION":
                result["NEEDS_REVALIDATION"].append(signal_id)
            else:
                result["OPEN"].append(signal_id)
        return result

    def rebuild_projection(self, *, expected_version: int | None = None) -> dict[str, Any]:
        """Single SQLite write transaction implements the projection compare-and-swap."""
        try:
            self._begin()
            row = self.connection.execute("SELECT projection_version FROM projection_meta WHERE singleton = 1").fetchone()
            current = int(row["projection_version"]) if row else 0
            if expected_version is not None and expected_version != current:
                raise SignalPlaneError("STALE_PROJECTION_VERSION", "/expected_projection_version", "stale projection writer rejected")
            projection = self._reduce()
            projection["projection_version"] = current + 1
            projection["generated_at"] = f"deterministic-input-revision:{projection['input_revision']}"
            checksum_input = {key: value for key, value in projection.items() if key not in {"checksum", "projection_version", "generated_at"}}
            projection["checksum"] = _checksum(checksum_input)
            self.connection.execute(
                "INSERT INTO projection_meta(singleton,projection_version,input_revision,checksum,projection_json) VALUES(1,?,?,?,?) "
                "ON CONFLICT(singleton) DO UPDATE SET projection_version=excluded.projection_version,input_revision=excluded.input_revision,checksum=excluded.checksum,projection_json=excluded.projection_json",
                (projection["projection_version"], projection["input_revision"], projection["checksum"], _canonical(projection)),
            )
            self.connection.commit()
            return projection
        except SignalPlaneError:
            self._rollback()
            raise
        except sqlite3.Error as exc:
            self._rollback()
            raise SignalPlaneError("PROJECTION_CAS_FAILED", "/projection", "durable projection transaction failed") from exc

    def observe_replay(self) -> bool:
        first = self.rebuild_projection(expected_version=self.current_projection_version())
        self.discard_projection_for_recovery_test()
        second = self.rebuild_projection(expected_version=self.current_projection_version())
        return first["checksum"] == second["checksum"]

    def discard_projection_for_recovery_test(self) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM projection_meta")

    def compact_snapshot(self) -> dict[str, Any]:
        projection = self.rebuild_projection(expected_version=self.current_projection_version())
        return {"snapshot_ref": f"projection:{projection['projection_version']}", "checksum": projection["checksum"], "history_retained": True}
