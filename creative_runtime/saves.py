"""Fail-closed v1 migration and v2 durable save envelopes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from .contracts import PlayerAction, StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation, apply_state_patch
from .scene_graph import SceneGraph, initial_story_state


V1_SCHEMA = "CreativeSession/v1"
V2_SCHEMA = "CreativeSession/v2"
_SLOT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class SaveViolation(LedgerViolation):
    pass


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _story_semantics(state: StoryState) -> dict[str, Any]:
    return {
        "relationships": dict(state.relationships),
        "known_facts": list(state.known_facts),
        "risk_level": state.risk_level,
        "flags": dict(state.flags),
    }


def _legacy_options() -> dict[str, dict[str, dict[str, Any]]]:
    # Canonical predecessor semantics, retained solely to validate an existing
    # v1 record before considering a migration.
    return {
        "arrival": {
            "listen": {"patch": {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}, "mapped": "listen"},
            "approach": {"patch": {"beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}, "mapped": "knock"},
            "leave": {"patch": {"beat_id": "courtyard", "risk_delta": -1, "flags": {"arrival": "deferred"}}, "mapped": "defer"},
        },
        "echo": {
            "approach": {"patch": {"beat_id": "threshold", "relationship_delta": {"mira": 1}}, "mapped": "knock"},
            "leave": {"patch": {"beat_id": "courtyard", "flags": {"clue": "recorded"}}, "mapped": "record"},
        },
        "threshold": {
            "listen": {"patch": {"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1}, "mapped": "promise"},
            "leave": {"patch": {"beat_id": "courtyard", "flags": {"meeting": "offered"}}, "mapped": "retreat"},
        },
    }


def _make_action_payload(action_id: str, transition_id: str, patch: Mapping[str, Any], text: str) -> dict[str, Any]:
    return {
        "action": PlayerAction(action_id, "choice", text).to_dict(),
        "transition_id": transition_id,
        "resulting_patch": dict(patch),
    }


def _legacy_records_from_receipt(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = receipt.get("legacy_records")
    if not isinstance(records, list) or not all(isinstance(record, Mapping) for record in records):
        raise SaveViolation("migration receipt has no typed legacy_records")
    return [dict(record) for record in records]


def _migrate_records(records: list[Mapping[str, Any]], source_digest: str) -> CreativeLedger:
    legacy = CreativeLedger.from_records(records)
    if not legacy.events or legacy.events[0].event_type != "story_initialized":
        raise SaveViolation("legacy session lacks story_initialized")
    legacy_initial = StoryState.from_dict(legacy.events[0].payload.get("state", {}))
    if legacy_initial.scene_id != "synthetic_archive" or legacy_initial.beat_id != "arrival":
        raise SaveViolation("legacy initial state is noncanonical")

    graph = SceneGraph()
    migrated = CreativeLedger()
    migrated.append("story_initialized", {"state": initial_story_state().to_dict()}, legacy.events[0].occurred_at)
    old_state = legacy_initial
    new_state = initial_story_state()
    bridge_added = False
    for index, event in enumerate(legacy.events[1:], start=1):
        if event.event_type != "player_action":
            raise SaveViolation("legacy event is not a player_action")
        action = event.payload.get("action")
        if not isinstance(action, Mapping):
            raise SaveViolation("legacy action is malformed")
        action_id = str(action.get("action_id", ""))
        option = _legacy_options().get(old_state.beat_id, {}).get(action_id)
        if option is None:
            raise SaveViolation("legacy action is noncanonical")
        old_patch = option["patch"]
        patch = event.payload.get("resulting_patch")
        if not isinstance(patch, Mapping) or dict(patch) != dict(old_patch):
            raise SaveViolation("legacy resulting_patch does not match predecessor semantics")
        old_state = apply_state_patch(old_state, old_patch)
        transition, new_state = graph.transition(new_state, str(option["mapped"]))
        if _story_semantics(old_state) != _story_semantics(new_state):
            raise SaveViolation("LOSSY_UNREPRESENTABLE legacy transition at index " + str(index))
        migrated.append(
            "player_action",
            _make_action_payload(str(option["mapped"]), transition.transition_id, transition.patch, str(action.get("text", action_id))),
            event.occurred_at,
        )
        # The only bridge is deterministic and typed: threshold/listen's old
        # terminal name becomes the current accord state after equivalence is
        # proven. It is regenerated from the complete legacy source below.
        if old_state.beat_id == "resolution" and not bridge_added:
            migrated.append(
                "migration_bridge",
                {"kind": "legacy_terminal_resolution", "source_digest": source_digest, "patch": {}},
                event.occurred_at,
            )
            bridge_added = True
    return migrated


@dataclass
class SavedSession:
    ledger: CreativeLedger
    migration_receipt: Mapping[str, Any] | None = None
    migration_history: tuple[Mapping[str, Any], ...] = ()

    def validate(self) -> StoryState:
        self.ledger.verify_chain()
        if self.migration_receipt is not None:
            receipt = self.migration_receipt
            records = _legacy_records_from_receipt(receipt)
            raw = canonical_json({"schema": V1_SCHEMA, "events": records}).encode("utf-8")
            if receipt.get("source_digest") != _digest_bytes(raw):
                raise SaveViolation("migration receipt source digest mismatch")
            expected = _migrate_records(records, str(receipt["source_digest"]))
            prefix_count = int(receipt.get("prefix_event_count", -1))
            if prefix_count != len(expected.events):
                raise SaveViolation("migration receipt prefix length mismatch")
            if self.ledger.to_records()[:prefix_count] != expected.to_records():
                raise SaveViolation("migration bridge provenance does not regenerate exact prefix")
            expected_history = ({"source_digest": receipt["source_digest"], "kind": "legacy_v1_to_v2"},)
            if tuple(dict(item) for item in self.migration_history) != expected_history:
                raise SaveViolation("migration history is not ledger-bound")
        elif self.migration_history:
            raise SaveViolation("native v2 session must not carry migration history")

        if not self.ledger.events or self.ledger.events[0].event_type != "story_initialized":
            raise SaveViolation("session must start with story_initialized")
        state = StoryState.from_dict(self.ledger.events[0].payload.get("state", {}))
        if state != initial_story_state():
            raise SaveViolation("v2 session initial state is not canonical")
        graph = SceneGraph()
        bridge_seen = False
        for event in self.ledger.events[1:]:
            if event.event_type == "player_action":
                try:
                    state = graph.validate_action_record(state, event.payload)
                except LedgerViolation as error:
                    raise SaveViolation(str(error)) from error
            elif event.event_type == "migration_bridge":
                if self.migration_receipt is None or bridge_seen:
                    raise SaveViolation("unbound or repeated migration_bridge")
                bridge_seen = True
                if event.payload.get("kind") != "legacy_terminal_resolution" or event.payload.get("source_digest") != self.migration_receipt.get("source_digest") or event.payload.get("patch") != {}:
                    raise SaveViolation("migration_bridge payload is not canonical")
            else:
                raise SaveViolation("unsupported session event type: " + event.event_type)
        return state

    def state(self) -> StoryState:
        return self.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": V2_SCHEMA,
            "events": self.ledger.to_records(),
            "migration_receipt": dict(self.migration_receipt) if self.migration_receipt is not None else None,
            "migration_history": [dict(item) for item in self.migration_history],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SavedSession":
        if value.get("schema") != V2_SCHEMA:
            raise SaveViolation("unsupported session schema")
        receipt = value.get("migration_receipt")
        if receipt is not None and not isinstance(receipt, Mapping):
            raise SaveViolation("migration receipt is malformed")
        history = value.get("migration_history", [])
        if not isinstance(history, list) or not all(isinstance(item, Mapping) for item in history):
            raise SaveViolation("migration history is malformed")
        session = cls(CreativeLedger.from_records(value.get("events", [])), dict(receipt) if receipt else None, tuple(dict(item) for item in history))
        session.validate()
        return session


class SaveStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def legacy_path(self) -> Path:
        return self.workspace / "session.json"

    def path_for(self, slot: str = "default") -> Path:
        if not _SLOT.fullmatch(slot):
            raise SaveViolation("unsafe save slot")
        return self.workspace / "saves" / f"{slot}.json"

    def create_initial(self) -> SavedSession:
        ledger = CreativeLedger()
        ledger.append("story_initialized", {"state": initial_story_state().to_dict()}, "2030-01-01T00:00:00Z")
        session = SavedSession(ledger)
        session.validate()
        return session

    def save(self, session: SavedSession, slot: str = "default") -> Path:
        session.validate()
        path = self.path_for(slot)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(session.to_dict()) + "\n", encoding="utf-8")
        return path

    def _migrate_legacy(self, path: Path) -> SavedSession:
        raw = path.read_bytes()
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SaveViolation("legacy session is malformed") from error
        if document.get("schema") != V1_SCHEMA or not isinstance(document.get("events"), list):
            raise SaveViolation("legacy session schema is unsupported")
        records = [dict(record) for record in document["events"] if isinstance(record, Mapping)]
        if len(records) != len(document["events"]):
            raise SaveViolation("legacy session records are malformed")
        source_digest = _digest_bytes(canonical_json({"schema": V1_SCHEMA, "events": records}).encode("utf-8"))
        ledger = _migrate_records(records, source_digest)
        receipt = {"source_digest": source_digest, "legacy_records": records, "prefix_event_count": len(ledger.events)}
        session = SavedSession(ledger, receipt, ({"source_digest": source_digest, "kind": "legacy_v1_to_v2"},))
        session.validate()
        return session

    def load(self, slot: str = "default") -> SavedSession:
        path = self.path_for(slot)
        if path.is_file():
            try:
                return SavedSession.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as error:
                raise SaveViolation("v2 session is malformed") from error
        legacy = self.legacy_path()
        if slot == "default" and legacy.is_file():
            # Migration is deliberately all-or-nothing. A failure returns before
            # any v2 path is created, so an old source cannot be shadowed.
            session = self._migrate_legacy(legacy)
            self.save(session, slot)
            return session
        raise SaveViolation("No session exists; run init first")

    def append_choice(self, session: SavedSession, action_id: str, text: str, occurred_at: str) -> SavedSession:
        state = session.state()
        transition, _ = SceneGraph().transition(state, action_id)
        session.ledger.append("player_action", _make_action_payload(action_id, transition.transition_id, transition.patch, text), occurred_at)
        session.validate()
        return session
