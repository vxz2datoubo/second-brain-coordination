"""SQLite-backed append-only ledger and deterministic projection reducer."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .models import SignalEvent, SignalLink, SignalPlaneError


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _checksum(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class DurableSignalLedger:
    """Durable local ledger: history is authoritative; projections are derived and rebuildable."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS admitted_events (
              ledger_offset INTEGER PRIMARY KEY AUTOINCREMENT, event_source TEXT NOT NULL, event_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL, semantic_hash TEXT NOT NULL, record_json TEXT NOT NULL,
              UNIQUE(event_source, event_id)
            );
            CREATE TABLE IF NOT EXISTS signal_links (
              link_id TEXT PRIMARY KEY, record_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projection_meta (
              singleton INTEGER PRIMARY KEY CHECK(singleton = 1), projection_version INTEGER NOT NULL,
              checksum TEXT NOT NULL, projection_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rejected_events (
              reject_id INTEGER PRIMARY KEY AUTOINCREMENT, reason_code TEXT NOT NULL, path TEXT NOT NULL,
              payload_fingerprint TEXT NOT NULL
            );
        """)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def ingest_raw(self, payload: Mapping[str, Any], *, update_projection: bool = True) -> dict[str, Any]:
        try:
            event = SignalEvent.from_dict(payload)
        except SignalPlaneError as exc:
            fingerprint = _checksum(payload if isinstance(payload, Mapping) else {"not_object": True})
            with self.connection:
                self.connection.execute("INSERT INTO rejected_events(reason_code, path, payload_fingerprint) VALUES (?, ?, ?)", (exc.code, exc.path, fingerprint))
            return {"status": "REJECTED", "code": exc.code, "path": exc.path, "quarantined": True}
        return self.ingest(event, update_projection=update_projection)

    def ingest(self, event: SignalEvent, *, update_projection: bool = True) -> dict[str, Any]:
        snapshot, semantic_hash, key = event.as_dict(), event.semantic_hash, event.idempotency_key
        with self.connection:
            same_key = self.connection.execute("SELECT ledger_offset, semantic_hash FROM admitted_events WHERE idempotency_key = ? ORDER BY ledger_offset LIMIT 1", (key,)).fetchone()
            if same_key:
                if same_key["semantic_hash"] != semantic_hash:
                    raise SignalPlaneError("IDEMPOTENCY_KEY_COLLISION", "/idempotency_key", "same idempotency key carries different semantic content")
                return {"status": "IDEMPOTENT_DUPLICATE", "receipt_offset": same_key["ledger_offset"], "effective_state_changed": False}
            same_event = self.connection.execute("SELECT ledger_offset, semantic_hash FROM admitted_events WHERE event_source = ? AND event_id = ?", (snapshot["event_source"], snapshot["event_id"])).fetchone()
            if same_event:
                if same_event["semantic_hash"] != semantic_hash:
                    raise SignalPlaneError("EVENT_ID_COLLISION", "/event_id", "same source and event id carry different semantic content")
                return {"status": "IDEMPOTENT_DUPLICATE", "receipt_offset": same_event["ledger_offset"], "effective_state_changed": False}
            cursor = self.connection.execute("INSERT INTO admitted_events(event_source,event_id,idempotency_key,semantic_hash,record_json) VALUES (?, ?, ?, ?, ?)", (snapshot["event_source"], snapshot["event_id"], key, semantic_hash, _canonical(snapshot)))
            offset = cursor.lastrowid
        if update_projection:
            self.rebuild_projection(expected_version=self.current_projection_version())
        return {"status": "ADMITTED", "receipt_offset": offset, "effective_state_changed": True}

    def append_link(self, link: SignalLink) -> None:
        with self.connection:
            existing = self.connection.execute("SELECT record_json FROM signal_links WHERE link_id = ?", (link.link_id,)).fetchone()
            if existing and existing["record_json"] != _canonical(link.as_dict()):
                raise SignalPlaneError("LINK_ID_COLLISION", "/link_id", "link ids are immutable")
            if not existing:
                self.connection.execute("INSERT INTO signal_links(link_id, record_json) VALUES (?, ?)", (link.link_id, _canonical(link.as_dict())))

    def history(self) -> list[dict[str, Any]]:
        return [json.loads(row["record_json"]) | {"ledger_offset": row["ledger_offset"]} for row in self.connection.execute("SELECT ledger_offset, record_json FROM admitted_events ORDER BY ledger_offset")]

    def rejected_count(self) -> int:
        return int(self.connection.execute("SELECT count(*) FROM rejected_events").fetchone()[0])

    def current_projection_version(self) -> int:
        row = self.connection.execute("SELECT projection_version FROM projection_meta WHERE singleton = 1").fetchone()
        return int(row["projection_version"]) if row else 0

    def current_projection(self) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT projection_json FROM projection_meta WHERE singleton = 1").fetchone()
        return json.loads(row["projection_json"]) if row else None

    def _reduce(self) -> dict[str, Any]:
        signals: dict[str, dict[str, Any]] = {}
        ranks = {"NOT_STARTED": 0, "AUTHORIZED": 1, "EXECUTING": 2, "REVIEW": 3, "DONE": 4, "BLOCKED": 4, "CANCELLED": 5}
        for event in self.history():
            key = event["signal_id"]
            order = event.get("source_sequence") if event.get("source_sequence") is not None else event["ledger_offset"]
            current = signals.get(key)
            current_order = current.get("source_order", -1) if current else -1
            if order < current_order:
                continue  # stale views never regress effective state
            if current and ranks[event["execution_state"]] < ranks[current["execution_state"]] and event["execution_state"] not in {"CANCELLED", "BLOCKED"}:
                continue
            signals[key] = {"signal_id": key, "planning_state": event["planning_state"], "execution_state": event["execution_state"], "epistemic_state": event["epistemic_state"], "source_order": order, "provenance_event_refs": sorted(set((current or {}).get("provenance_event_refs", []) + [event["event_id"]]))}
            for target in event["revokes_refs"]:
                if target in signals:
                    signals[target]["planning_state"] = "SUPERSEDED"
                    signals[target]["execution_state"] = "CANCELLED"
        links = [json.loads(row["record_json"]) for row in self.connection.execute("SELECT record_json FROM signal_links ORDER BY link_id")]
        return {"reducer_version": "S0C-1", "ledger_watermark": len(self.history()), "signals": [signals[key] for key in sorted(signals)], "links": links, "clusters": [], "views": self._views(signals)}

    @staticmethod
    def _views(signals: Mapping[str, Mapping[str, Any]]) -> dict[str, list[str]]:
        result = {name: [] for name in ("OPEN", "BLOCKED", "SUPERSEDED", "CLOSED_NO_ACTION", "NEEDS_REVALIDATION")}
        for signal_id, state in signals.items():
            if state["planning_state"] == "SUPERSEDED": result["SUPERSEDED"].append(signal_id)
            elif state["execution_state"] == "BLOCKED": result["BLOCKED"].append(signal_id)
            elif state["planning_state"] == "CLOSED_NO_ACTION": result["CLOSED_NO_ACTION"].append(signal_id)
            elif state["epistemic_state"] == "NEEDS_REVALIDATION": result["NEEDS_REVALIDATION"].append(signal_id)
            else: result["OPEN"].append(signal_id)
        return result

    def rebuild_projection(self, *, expected_version: int | None = None) -> dict[str, Any]:
        current = self.current_projection_version()
        if expected_version is not None and expected_version != current:
            raise SignalPlaneError("STALE_PROJECTION_VERSION", "/expected_projection_version", "stale projection writer rejected")
        projection = self._reduce()
        projection["projection_version"] = projection["ledger_watermark"]
        projection["generated_at"] = f"deterministic-watermark:{projection['ledger_watermark']}"
        projection["checksum"] = _checksum({key: value for key, value in projection.items() if key != "checksum"})
        with self.connection:
            self.connection.execute("INSERT INTO projection_meta(singleton,projection_version,checksum,projection_json) VALUES(1,?,?,?) ON CONFLICT(singleton) DO UPDATE SET projection_version=excluded.projection_version, checksum=excluded.checksum, projection_json=excluded.projection_json", (projection["projection_version"], projection["checksum"], _canonical(projection)))
        return projection

    def discard_projection_for_recovery_test(self) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM projection_meta")

    def compact_snapshot(self) -> dict[str, Any]:
        projection = self.rebuild_projection(expected_version=self.current_projection_version())
        return {"snapshot_ref": f"projection:{projection['projection_version']}", "checksum": projection["checksum"], "history_retained": True}
