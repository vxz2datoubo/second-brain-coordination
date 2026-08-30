"""Fail-closed v1-to-v2 session migration with durable source-byte binding.

The v2 receipt is treated as untrusted storage.  On every validation it is
re-derived from the still-present v1 ``session.json`` rather than trusted as a
proof of its own origin.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from .contracts import PlayerAction, StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation, apply_state_patch
from .scene_graph import initial, move

V1 = "CreativeSession/v1"
V2 = "CreativeSession/v2"

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _legacy_step(state: StoryState, action: str) -> StoryState:
    rules = {
        ("arrival", "listen"): {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1},
        ("arrival", "approach"): {"beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}},
        ("arrival", "leave"): {"beat_id": "courtyard", "risk_delta": -1, "flags": {"arrival": "deferred"}},
        ("echo", "approach"): {"beat_id": "threshold", "relationship_delta": {"mira": 1}},
        ("echo", "leave"): {"beat_id": "courtyard", "flags": {"clue": "recorded"}},
        ("threshold", "listen"): {"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1},
        ("threshold", "leave"): {"beat_id": "courtyard", "flags": {"meeting": "offered"}},
    }
    patch = rules.get((state.beat_id, action))
    if patch is None:
        raise LedgerViolation("Unknown legacy route")
    return apply_state_patch(state, patch)

def _parse_legacy(raw: bytes) -> tuple[list[Mapping[str, Any]], list[str], StoryState]:
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LedgerViolation("Legacy source is not valid JSON") from error
    if envelope.get("schema") != V1 or not isinstance(envelope.get("events"), list):
        raise LedgerViolation("Legacy source schema is unsupported")
    records = envelope["events"]
    ledger = CreativeLedger.from_records(records)
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise LedgerViolation("Legacy source has no canonical initializer")
    state = StoryState.from_dict(ledger.events[0].payload.get("state", {}))
    if (state.scene_id, state.beat_id) != ("synthetic_archive", "arrival"):
        raise LedgerViolation("Legacy source starts outside the canonical fixture")
    actions: list[str] = []
    for event in ledger.events[1:]:
        if event.event_type != "player_action":
            raise LedgerViolation("Legacy event is not a player action")
        payload = event.payload
        action_data, patch = payload.get("action"), payload.get("resulting_patch")
        if not isinstance(action_data, Mapping) or not isinstance(patch, Mapping):
            raise LedgerViolation("Legacy action payload is malformed")
        action = str(action_data.get("action_id", ""))
        expected = _legacy_step(state, action)
        if apply_state_patch(state, patch) != expected:
            raise LedgerViolation("Legacy patch differs from canonical historic semantics")
        actions.append(action)
        state = expected
    return records, actions, state

def _same_story_effect(a: StoryState, b: StoryState) -> bool:
    return (dict(a.relationships), tuple(a.known_facts), a.risk_level, dict(a.flags)) == (dict(b.relationships), tuple(b.known_facts), b.risk_level, dict(b.flags))

def _translate(state: StoryState, legacy_action: str) -> str:
    if legacy_action == "approach": return "knock"
    if legacy_action == "listen": return "promise" if state.scene_id == "interior_archive" else "listen"
    if legacy_action == "leave":
        if state.beat_id == "arrival": return "defer"
        if state.beat_id == "echo": return "record"
        if (state.scene_id, state.beat_id) == ("interior_archive", "threshold"): return "retreat"
    raise LedgerViolation("Legacy action has no safe v2 translation")

def _append_move(ledger: CreativeLedger, state: StoryState, action: str, clock: int) -> StoryState:
    item, next_state = move(state, action)
    ledger.append("player_action", {"action": PlayerAction(action, "choice", action).to_dict(), "transition_id": item.transition, "resulting_patch": dict(item.patch)}, f"2030-01-01T00:{clock:02d}:00Z")
    return next_state

def _derive_from_source(raw: bytes) -> tuple[dict[str, Any], CreativeLedger]:
    records, legacy_actions, legacy_final = _parse_legacy(raw)
    receipt = {"source_digest": _sha(raw), "legacy_records": records}
    ledger = CreativeLedger()
    state = initial()
    ledger.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
    for index, old_action in enumerate(legacy_actions, 1):
        state = _append_move(ledger, state, _translate(state, old_action), index)
    if not _same_story_effect(state, legacy_final):
        raise LedgerViolation("Legacy route is lossy under the v2 graph")
    if legacy_final.beat_id == "resolution":
        ledger.append("migration_bridge", {"kind": "legacy_terminal_resolution", "source_digest": receipt["source_digest"], "state_neutral": True}, f"2030-01-01T00:{len(ledger.events):02d}:00Z")
    return receipt, ledger

@dataclass(frozen=True)
class SavedSession:
    ledger: CreativeLedger
    migration: Mapping[str, Any] | None = None
    legacy_source_path: Path | None = None

    def validate(self) -> None:
        self.ledger.verify_chain()
        expected: CreativeLedger | None = None
        if self.migration is not None:
            if self.legacy_source_path is None or not self.legacy_source_path.is_file():
                raise LedgerViolation("Migrated session requires its immutable legacy source")
            actual_bytes = self.legacy_source_path.read_bytes()
            rederived_receipt, expected = _derive_from_source(actual_bytes)
            # The persisted receipt is untrusted; source bytes are authority.
            if dict(self.migration) != rederived_receipt:
                raise LedgerViolation("Migration receipt does not bind to immutable legacy source bytes")
            expected_records = expected.to_records()
            actual_records = self.ledger.to_records()
            expected_bridges = [(r["sequence"], r["event_id"]) for r in expected_records if r["event_type"] == "migration_bridge"]
            actual_bridges = [(r["sequence"], r["event_id"]) for r in actual_records if r["event_type"] == "migration_bridge"]
            if actual_bridges != expected_bridges:
                raise LedgerViolation("Migration bridge positions and identities differ from source reconstruction")
            if actual_records[:len(expected_records)] != expected_records:
                raise LedgerViolation("Migrated ledger prefix differs from immutable source reconstruction")
        self._state_unchecked()

    def _state_unchecked(self) -> StoryState:
        if not self.ledger.events or self.ledger.events[0].event_type != "story_initialized":
            raise LedgerViolation("Saved session has no initializer")
        state = StoryState.from_dict(self.ledger.events[0].payload.get("state", {}))
        if state != initial(): raise LedgerViolation("Saved session initial state is invalid")
        for event in self.ledger.events[1:]:
            if event.event_type == "migration_bridge":
                if event.payload.get("state_neutral") is not True: raise LedgerViolation("Migration bridge may not mutate story state")
                continue
            if event.event_type != "player_action": raise LedgerViolation("Saved session event type is forbidden")
            action = event.payload.get("action")
            if not isinstance(action, Mapping): raise LedgerViolation("Saved action is malformed")
            item, state2 = move(state, str(action.get("action_id", "")))
            if event.payload.get("transition_id") != item.transition or event.payload.get("resulting_patch") != item.patch:
                raise LedgerViolation("Saved action disagrees with graph authority")
            state = state2
        return state

    def state(self) -> StoryState:
        self.validate()
        return self._state_unchecked()

class SaveStore:
    def __init__(self, workspace: Path) -> None: self.workspace = workspace
    @property
    def legacy_path(self) -> Path: return self.workspace / "session.json"
    @property
    def save_path(self) -> Path: return self.workspace / "saves" / "default.json"
    def write(self, session: SavedSession) -> None:
        session.validate(); self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.save_path.write_text(canonical_json({"schema": V2, "events": session.ledger.to_records(), "migration": session.migration}) + "\n", encoding="utf-8")
    def load(self) -> SavedSession:
        if self.save_path.exists():
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
            if data.get("schema") != V2: raise LedgerViolation("Saved session schema is unsupported")
            session = SavedSession(CreativeLedger.from_records(data.get("events", [])), data.get("migration"), self.legacy_path if data.get("migration") is not None else None)
            session.validate(); return session
        if self.legacy_path.exists():
            original = self.legacy_path.read_bytes(); receipt, ledger = _derive_from_source(original)
            session = SavedSession(ledger, receipt, self.legacy_path); self.write(session)
            if self.legacy_path.read_bytes() != original: raise LedgerViolation("Legacy source bytes changed during migration")
            return session
        raise LedgerViolation("No saved session exists")
