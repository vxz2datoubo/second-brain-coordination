"""Fail-closed v2 session storage and lossless v1 migration.

The store separates **integrity** (the append-only event hash chain) from
**authority** (an event's right to affect story state).  A save editor can
recompute hashes, so a general ``state_patch`` is never trusted.  The only
exception is represented as a typed ``migration_bridge`` and is accepted only
when its complete deterministic v1 source migration can be regenerated.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .contracts import PlayerAction, StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation, digest
from .scene_graph import DEFAULT_SCENE_GRAPH, SceneGraph, SceneGraphViolation


SESSION_SCHEMA = "CreativeSession/v2"
LEGACY_SCHEMA = "CreativeSession/v1"
_SLOT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class SaveViolation(LedgerViolation):
    """A session is malformed, unauthorised, or cannot be losslessly migrated."""


@dataclass(frozen=True)
class MigrationReceipt:
    source_digest: str
    legacy_event_count: int
    bridge_event_id: str | None
    legacy_records: tuple[Mapping[str, Any], ...]
    mapping_version: str = "legacy-v1-to-v2-r165"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_digest": self.source_digest,
            "legacy_event_count": self.legacy_event_count,
            "bridge_event_id": self.bridge_event_id,
            "legacy_records": [dict(item) for item in self.legacy_records],
            "mapping_version": self.mapping_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MigrationReceipt":
        return cls(
            source_digest=str(value["source_digest"]),
            legacy_event_count=int(value["legacy_event_count"]),
            bridge_event_id=(str(value["bridge_event_id"]) if value.get("bridge_event_id") else None),
            legacy_records=tuple(dict(item) for item in value["legacy_records"]),
            mapping_version=str(value.get("mapping_version", "")),
        )


@dataclass(frozen=True)
class SavedSession:
    ledger: CreativeLedger
    migration_receipt: MigrationReceipt | None = None
    migration_history: tuple[Mapping[str, Any], ...] = ()

    def state(self) -> StoryState:
        return _validated_replay(self.ledger, self.migration_receipt, self.migration_history)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_slot(slot: str) -> str:
    if not _SLOT.fullmatch(slot):
        raise SaveViolation("Invalid save slot")
    return slot


def _legacy_action_id(state: StoryState, old_action: str) -> str:
    """Map canonical old vocabulary to the v2 graph without weakening it."""

    if old_action == "listen" and state.beat_id == "arrival":
        return "listen"
    if old_action == "approach":
        return "knock"
    if old_action == "leave":
        if state.beat_id == "echo":
            return "record"
        if state.beat_id == "threshold":
            return "retreat"
        return "defer"
    if old_action == "listen" and state.beat_id == "threshold":
        return "promise"
    raise SaveViolation("Legacy action is not losslessly representable")


def _legacy_expected_patch(state: StoryState, action_id: str) -> Mapping[str, Any]:
    transition = DEFAULT_SCENE_GRAPH.transition_for(state, action_id)
    return transition.patch


def _verify_legacy_patch(old_patch: Mapping[str, Any], old_state: StoryState, old_action: str) -> None:
    """Reject a v1 record unless its old patch is the actual canonical rule."""

    expected: dict[str, Any]
    if old_state.beat_id == "arrival" and old_action == "listen":
        expected = {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}
    elif old_state.beat_id in {"arrival", "echo"} and old_action == "approach":
        expected = {"beat_id": "threshold", "relationship_delta": {"mira": 1}}
        if old_state.beat_id == "arrival":
            expected["flags"] = {"arrival": "announced"}
    elif old_state.beat_id == "threshold" and old_action == "listen":
        expected = {"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1}
    elif old_action == "leave":
        expected = {"beat_id": "courtyard"}
        if old_state.beat_id == "arrival":
            expected.update({"risk_delta": -1, "flags": {"arrival": "deferred"}})
        elif old_state.beat_id == "echo":
            expected["flags"] = {"clue": "recorded"}
        elif old_state.beat_id == "threshold":
            expected["flags"] = {"meeting": "offered"}
        else:
            raise SaveViolation("Legacy action is not canonical for its beat")
    else:
        raise SaveViolation("Unknown legacy action")
    if dict(old_patch) != expected:
        raise SaveViolation("Legacy resulting_patch is not canonical")


def migrate_legacy_records(records: list[Mapping[str, Any]]) -> tuple[CreativeLedger, MigrationReceipt, tuple[Mapping[str, Any], ...]]:
    """Mechanically migrate only canonical, lossless v1 session records.

    The generated record sequence is deterministic and later used as the
    immutable migration prefix.  Continuation records may follow it, but no
    second bridge or replacement migration source can be inserted.
    """

    try:
        legacy = CreativeLedger.from_records(records)
    except (KeyError, TypeError, ValueError, LedgerViolation) as error:
        raise SaveViolation("Legacy event chain is invalid") from error
    if not legacy.events or legacy.events[0].event_type != "story_initialized":
        raise SaveViolation("Legacy session must begin with story_initialized")
    first = StoryState.from_dict(legacy.events[0].payload.get("state", {}))
    if (first.scene_id, first.beat_id) != ("synthetic_archive", "arrival"):
        raise SaveViolation("Legacy initial state is not canonical")

    migrated = CreativeLedger()
    migrated.append(
        "story_initialized", {"state": DEFAULT_SCENE_GRAPH.initial_state.to_dict()},
        "2030-01-01T00:00:00Z",
    )
    current_old = first
    current_new = DEFAULT_SCENE_GRAPH.initial_state
    history: list[Mapping[str, Any]] = []
    bridge_id: str | None = None
    for index, event in enumerate(legacy.events[1:], start=1):
        if event.event_type != "player_action":
            raise SaveViolation("Legacy sessions may contain only player_action events after init")
        action = event.payload.get("action")
        patch = event.payload.get("resulting_patch")
        if not isinstance(action, Mapping) or not isinstance(patch, Mapping):
            raise SaveViolation("Legacy player_action is malformed")
        old_action = str(action.get("action_id", ""))
        _verify_legacy_patch(patch, current_old, old_action)
        next_action = _legacy_action_id(current_new, old_action)
        transition = DEFAULT_SCENE_GRAPH.transition_for(current_new, next_action)
        occurred_at = f"2030-01-01T00:{index:02d}:00Z"
        # The old terminal resolution maps only to the v2 accord bridge.  It is
        # encoded separately so normal callers can never mint the same event.
        if current_old.beat_id == "threshold" and old_action == "listen":
            bridge = migrated.append(
                "migration_bridge",
                {
                    "kind": "legacy_resolution_terminal",
                    "legacy_sequence": event.sequence,
                    "transition_id": transition.transition_id,
                    "patch": dict(transition.patch),
                },
                occurred_at,
            )
            bridge_id = bridge.event_id
        else:
            migrated.append(
                "player_action",
                {
                    "action": PlayerAction(next_action, "legacy_migrated_choice", str(action.get("text", old_action))).to_dict(),
                    "transition_id": transition.transition_id,
                    "resulting_patch": dict(transition.patch),
                },
                occurred_at,
            )
        history.append({"legacy_sequence": event.sequence, "legacy_action": old_action, "v2_transition": transition.transition_id})
        # Old-state replay is safe only after exact canonical patch validation.
        from .ledger import apply_state_patch
        current_old = apply_state_patch(current_old, patch)
        current_new = apply_state_patch(current_new, transition.patch)

    receipt = MigrationReceipt(
        source_digest=digest({"schema": LEGACY_SCHEMA, "events": records}),
        legacy_event_count=len(records),
        bridge_event_id=bridge_id,
        legacy_records=tuple(dict(item) for item in records),
    )
    return migrated, receipt, tuple(history)


def _validated_replay(
    ledger: CreativeLedger, receipt: MigrationReceipt | None, history: tuple[Mapping[str, Any], ...]
) -> StoryState:
    """Validate all authority before exposing a state to any consumer."""

    ledger.verify_chain()
    expected_prefix: list[dict[str, Any]] | None = None
    if receipt is not None:
        legacy_records = [dict(item) for item in receipt.legacy_records]
        if receipt.legacy_event_count != len(legacy_records):
            raise SaveViolation("Migration receipt legacy event count is inconsistent")
        if receipt.source_digest != digest({"schema": LEGACY_SCHEMA, "events": legacy_records}):
            raise SaveViolation("Migration receipt source digest is inconsistent")
        regenerated, regenerated_receipt, regenerated_history = migrate_legacy_records(legacy_records)
        if regenerated_receipt.bridge_event_id != receipt.bridge_event_id or tuple(regenerated_history) != history:
            raise SaveViolation("Migration receipt does not match deterministic source migration")
        expected_prefix = regenerated.to_records()
        actual = ledger.to_records()
        if actual[:len(expected_prefix)] != expected_prefix:
            raise SaveViolation("Migrated session does not begin with deterministic source-bound prefix")
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise SaveViolation("Session must start with story_initialized")
    state = StoryState.from_dict(ledger.events[0].payload.get("state", {}))
    if (state.scene_id, state.beat_id) != ("archive_gate", "arrival"):
        raise SaveViolation("v2 initial state is not canonical")
    bridge_seen = False
    for position, event in enumerate(ledger.events[1:], start=1):
        if event.event_type == "state_patch":
            raise SaveViolation("state_patch is never accepted from a v2 save")
        if event.event_type == "player_action":
            if bridge_seen and receipt is None:
                raise SaveViolation("Post-bridge session lacks migration receipt")
            state = DEFAULT_SCENE_GRAPH.verify_event(state, event.payload)
            continue
        if event.event_type == "migration_bridge":
            if bridge_seen or receipt is None or receipt.bridge_event_id != event.event_id:
                raise SaveViolation("migration bridge is not authorised by this receipt")
            if state != StoryState(scene_id="interior_archive", beat_id="threshold", relationships=state.relationships,
                                   known_facts=state.known_facts, risk_level=state.risk_level, flags=state.flags):
                # State equality is deliberately explicit about the only allowed
                # source position, while keeping relationship/fact history intact.
                raise SaveViolation("migration bridge appears outside its terminal prefix")
            if event.payload.get("kind") != "legacy_resolution_terminal":
                raise SaveViolation("Unknown migration bridge kind")
            expected = DEFAULT_SCENE_GRAPH.transition_for(state, "promise")
            if event.payload.get("transition_id") != expected.transition_id or event.payload.get("patch") != dict(expected.patch):
                raise SaveViolation("migration bridge does not equal the canonical terminal mapping")
            state = DEFAULT_SCENE_GRAPH.apply(state, "promise")[1]
            bridge_seen = True
            continue
        raise SaveViolation("Unsupported session event type")
    if receipt is None and history:
        raise SaveViolation("Native v2 session contains migration history")
    if receipt is not None and receipt.mapping_version != "legacy-v1-to-v2-r165":
        raise SaveViolation("Unknown migration receipt version")
    if receipt is not None and expected_prefix is not None:
        bridge_positions = [index for index, item in enumerate(expected_prefix) if item["event_type"] == "migration_bridge"]
        if (bridge_positions[0] if bridge_positions else None) != (
            next((index for index, item in enumerate(ledger.to_records()) if item["event_type"] == "migration_bridge"), None)
        ):
            raise SaveViolation("Migration bridge was inserted outside its canonical prefix")
    return state


class SaveStore:
    """Workspace-local storage with slot confinement and lossless migration."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    @property
    def legacy_path(self) -> Path:
        return self.workspace / "session.json"

    def path_for(self, slot: str = "default") -> Path:
        return self.workspace / "saves" / (_safe_slot(slot) + ".json")

    def load(self, slot: str = "default") -> SavedSession:
        path = self.path_for(slot)
        if not path.is_file():
            raise SaveViolation("Save slot does not exist")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SaveViolation("Save file is unreadable") from error
        if record.get("schema") != SESSION_SCHEMA:
            raise SaveViolation("Unsupported save schema")
        try:
            ledger = CreativeLedger.from_records(record.get("events", []))
            receipt_raw = record.get("migration_receipt")
            receipt = MigrationReceipt.from_dict(receipt_raw) if isinstance(receipt_raw, Mapping) else None
            history_raw = record.get("migration_history", [])
            if not isinstance(history_raw, list) or not all(isinstance(item, Mapping) for item in history_raw):
                raise SaveViolation("Migration history is malformed")
            session = SavedSession(ledger, receipt, tuple(dict(item) for item in history_raw))
            session.state()
            return session
        except (KeyError, TypeError, ValueError, LedgerViolation) as error:
            raise SaveViolation("Save provenance validation failed") from error

    def save(self, session: SavedSession, slot: str = "default") -> Path:
        # Validate before writing so a caller cannot use save as an authority
        # laundering step.  Preserve receipt/history exactly on every write.
        session.state()
        path = self.path_for(slot)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"schema": SESSION_SCHEMA, "events": session.ledger.to_records()}
        if session.migration_receipt is not None:
            payload["migration_receipt"] = session.migration_receipt.to_dict()
            payload["migration_history"] = [dict(item) for item in session.migration_history]
        else:
            payload["migration_history"] = []
        path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        return path

    def initialize(self) -> tuple[SavedSession, str]:
        default = self.path_for()
        if default.exists():
            return self.load(), "already_initialized"
        if self.legacy_path.exists():
            original = self.legacy_path.read_bytes()
            try:
                record = json.loads(original.decode("utf-8"))
                if record.get("schema") != LEGACY_SCHEMA or not isinstance(record.get("events"), list):
                    raise SaveViolation("Unsupported legacy save schema")
                ledger, receipt, history = migrate_legacy_records(record["events"])
                session = SavedSession(ledger, receipt, history)
                session.state()
                self.save(session)
            except (UnicodeDecodeError, json.JSONDecodeError, SaveViolation, LedgerViolation, KeyError, TypeError, ValueError) as error:
                # The source is never opened for writing.  Importantly, no
                # default save is created when migration is incompatible.
                if self.legacy_path.read_bytes() != original:
                    raise SaveViolation("Legacy source changed during failed migration") from error
                raise SaveViolation("Legacy migration failed closed: " + str(error)) from error
            if self.legacy_path.read_bytes() != original:
                raise SaveViolation("Legacy source was modified by migration")
            return session, "migrated"
        ledger = CreativeLedger()
        ledger.append("story_initialized", {"state": DEFAULT_SCENE_GRAPH.initial_state.to_dict()}, "2030-01-01T00:00:00Z")
        session = SavedSession(ledger)
        self.save(session)
        return session, "initialized"
