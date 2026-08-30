"""Source-bound migration and fail-closed v2 saved-session access.

The security property is history equality, not merely final-state equality.
For a legacy source we rebuild the only permitted v2 history and compare every
migration bridge's *position and event identity* across the entire ledger.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import PlayerAction, StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation, apply_state_patch
from .scene_graph import apply_transition, initial_state, transition_for


V1_SCHEMA = "CreativeSession/v1"
V2_SCHEMA = "CreativeSession/v2"


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _equal_semantics(left: StoryState, right: StoryState) -> bool:
    return (
        dict(left.relationships) == dict(right.relationships)
        and tuple(left.known_facts) == tuple(right.known_facts)
        and left.risk_level == right.risk_level
        and dict(left.flags) == dict(right.flags)
    )


def _legacy_transition(state: StoryState, action: str) -> StoryState:
    # Canonical S00-S06 legacy rules, retained only to verify historical input.
    table: dict[tuple[str, str], Mapping[str, Any]] = {
        ("arrival", "listen"): {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1},
        ("arrival", "approach"): {"beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}},
        ("arrival", "leave"): {"beat_id": "courtyard", "risk_delta": -1, "flags": {"arrival": "deferred"}},
        ("echo", "approach"): {"beat_id": "threshold", "relationship_delta": {"mira": 1}},
        ("echo", "leave"): {"beat_id": "courtyard", "flags": {"clue": "recorded"}},
        ("threshold", "listen"): {"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1},
        ("threshold", "leave"): {"beat_id": "courtyard", "flags": {"meeting": "offered"}},
    }
    patch = table.get((state.beat_id, action))
    if patch is None:
        raise LedgerViolation("Unknown legacy action or beat")
    return apply_state_patch(state, patch)


def _legacy_actions(records: list[Mapping[str, Any]]) -> tuple[list[str], StoryState]:
    ledger = CreativeLedger.from_records(records)
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise LedgerViolation("Legacy session must begin with story_initialized")
    raw = ledger.events[0].payload.get("state")
    if not isinstance(raw, Mapping):
        raise LedgerViolation("Legacy initial state missing")
    state = StoryState.from_dict(raw)
    if state.scene_id != "synthetic_archive" or state.beat_id != "arrival":
        raise LedgerViolation("Legacy initial state is not canonical")
    actions: list[str] = []
    for event in ledger.events[1:]:
        if event.event_type != "player_action":
            raise LedgerViolation("Legacy event type is unsupported")
        raw_action = event.payload.get("action")
        patch = event.payload.get("resulting_patch")
        if not isinstance(raw_action, Mapping) or not isinstance(patch, Mapping):
            raise LedgerViolation("Legacy action payload missing")
        action = str(raw_action.get("action_id", ""))
        expected = _legacy_transition(state, action)
        actual = apply_state_patch(state, patch)
        if actual != expected:
            raise LedgerViolation("Legacy resulting_patch is not canonical")
        actions.append(action)
        state = expected
    return actions, state


def _mapped_action(state: StoryState, legacy_action: str) -> str:
    leave_target = (
        "defer" if state.beat_id == "arrival"
        else "record" if state.beat_id == "echo"
        else "retreat" if state.scene_id == "interior_archive" and state.beat_id == "threshold"
        else None
    )
    aliases = {"approach": "knock", "leave": leave_target, "listen": "listen"}
    if state.scene_id == "interior_archive" and legacy_action == "listen":
        return "promise"
    action = aliases.get(legacy_action)
    if action is None:
        raise LedgerViolation("Legacy action cannot be mapped")
    return action


def _append_action(ledger: CreativeLedger, state: StoryState, action_id: str, when: str) -> StoryState:
    transition, after = apply_transition(state, action_id)
    ledger.append("player_action", {
        "action": PlayerAction(action_id, "choice", action_id).to_dict(),
        "transition_id": transition.transition_id,
        "resulting_patch": dict(transition.patch),
    }, when)
    return after


@dataclass(frozen=True)
class SavedSession:
    ledger: CreativeLedger
    migration: Mapping[str, Any] | None = None

    def _expected_migrated_ledger(self) -> CreativeLedger | None:
        if self.migration is None:
            return None
        records = self.migration.get("legacy_records")
        if not isinstance(records, list):
            raise LedgerViolation("Migration receipt missing legacy records")
        actions, legacy_final = _legacy_actions(records)
        expected = CreativeLedger()
        state = initial_state()
        expected.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
        for index, legacy_action in enumerate(actions, 1):
            mapped = _mapped_action(state, legacy_action)
            state = _append_action(expected, state, mapped, f"2030-01-01T00:{index:02d}:00Z")
        # A terminal legacy resolution needs a typed, state-neutral marker.  It
        # is deterministic and its ID therefore becomes part of the receipt.
        if legacy_final.beat_id == "resolution":
            expected.append("migration_bridge", {
                "kind": "legacy_terminal_resolution", "source_digest": self.migration.get("source_digest"),
                "state_neutral": True,
            }, f"2030-01-01T00:{len(expected.events):02d}:00Z")
        if not _equal_semantics(state, legacy_final):
            raise LedgerViolation("Legacy route is lossy under the v2 graph")
        return expected

    def validate(self) -> None:
        self.ledger.verify_chain()
        if self.migration is not None:
            expected = self._expected_migrated_ledger()
            assert expected is not None
            expected_records = expected.to_records()
            actual_records = self.ledger.to_records()
            # This is deliberately whole-history equality.  Comparing only the
            # deterministic prefix would admit a later forged bridge whose hash
            # chain has been recomputed.
            expected_bridges = [(item["sequence"], item["event_id"]) for item in expected_records if item["event_type"] == "migration_bridge"]
            actual_bridges = [(item["sequence"], item["event_id"]) for item in actual_records if item["event_type"] == "migration_bridge"]
            if actual_bridges != expected_bridges:
                raise LedgerViolation("Migration bridge positions or identities do not match receipt")
            if actual_records[:len(expected_records)] != expected_records:
                raise LedgerViolation("Migrated deterministic prefix does not match its source receipt")
        self._replay_verified()

    def _replay_verified(self) -> StoryState:
        if not self.ledger.events or self.ledger.events[0].event_type != "story_initialized":
            raise LedgerViolation("Saved session must begin with story_initialized")
        state = StoryState.from_dict(self.ledger.events[0].payload["state"])
        if state != initial_state():
            raise LedgerViolation("Saved v2 initial state is not canonical")
        for event in self.ledger.events[1:]:
            if event.event_type == "migration_bridge":
                if event.payload.get("state_neutral") is not True:
                    raise LedgerViolation("Migration bridge may not change state")
                continue
            if event.event_type != "player_action":
                raise LedgerViolation("Saved v2 event type is unsupported")
            action = event.payload.get("action")
            if not isinstance(action, Mapping):
                raise LedgerViolation("Saved action missing")
            action_id = str(action.get("action_id", ""))
            transition = transition_for(state, action_id)
            if event.payload.get("transition_id") != transition.transition_id:
                raise LedgerViolation("Saved transition id disagrees with graph")
            patch = event.payload.get("resulting_patch")
            if not isinstance(patch, Mapping) or dict(patch) != dict(transition.patch):
                raise LedgerViolation("Saved patch disagrees with graph")
            state = apply_state_patch(state, transition.patch)
        return state

    def state(self) -> StoryState:
        self.validate()
        return self._replay_verified()


class SaveStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    @property
    def legacy_path(self) -> Path:
        return self.workspace / "session.json"

    @property
    def save_path(self) -> Path:
        return self.workspace / "saves" / "default.json"

    def create(self) -> SavedSession:
        if self.save_path.exists():
            return self.load()
        ledger = CreativeLedger()
        state = initial_state()
        ledger.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
        session = SavedSession(ledger)
        self.write(session)
        return session

    def _migrate_legacy(self, raw: bytes) -> SavedSession:
        data = json.loads(raw.decode("utf-8"))
        if data.get("schema") != V1_SCHEMA or not isinstance(data.get("events"), list):
            raise LedgerViolation("Unsupported legacy session schema")
        receipt = {"source_digest": _digest_bytes(raw), "legacy_records": data["events"]}
        # Build via the same receipt-driven function that validation uses.
        probe = SavedSession(CreativeLedger(), receipt)
        ledger = probe._expected_migrated_ledger()
        assert ledger is not None
        session = SavedSession(ledger, receipt)
        session.validate()
        return session

    def load(self) -> SavedSession:
        if self.save_path.exists():
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
            if data.get("schema") != V2_SCHEMA:
                raise LedgerViolation("Unsupported saved-session schema")
            session = SavedSession(CreativeLedger.from_records(data.get("events", [])), data.get("migration"))
            session.validate()
            return session
        if self.legacy_path.exists():
            original = self.legacy_path.read_bytes()
            session = self._migrate_legacy(original)
            # The legacy source is read-only.  A failed migration reaches this
            # point before any default v2 file is created.
            self.write(session)
            if self.legacy_path.read_bytes() != original:
                raise LedgerViolation("Legacy source changed during migration")
            return session
        raise LedgerViolation("No saved session exists; run init first")

    def write(self, session: SavedSession) -> None:
        session.validate()
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.save_path.write_text(canonical_json({"schema": V2_SCHEMA, "events": session.ledger.to_records(), "migration": session.migration}) + "\n", encoding="utf-8")

    def choose(self, action_id: str) -> SavedSession:
        session = self.load()
        state = session.state()
        ledger = CreativeLedger.from_records(session.ledger.to_records())
        _append_action(ledger, state, action_id, f"2030-01-01T00:{len(ledger.events):02d}:00Z")
        result = SavedSession(ledger, session.migration)
        result.validate()
        self.write(result)
        return result
