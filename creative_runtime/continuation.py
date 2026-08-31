"""Single-authority CreativeSession/v2 persistence, migration, continuation and review.

R171 deliberately keeps one persisted session envelope: an append-only CreativeLedger plus
an optional migration receipt. Legacy ``session.json`` bytes are immutable source evidence,
never a continuation store. Every read-facing consumer validates the same session object.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .contracts import PlayerAction, StoryState, canonical_json
from .director import compile_director
from .ledger import CreativeLedger, LedgerViolation, apply_state_patch


SCHEMA = "CreativeSession/v2"
MIGRATION_SCHEMA = "LegacyToV2MigrationReceipt/v1"
MAPPING_POLICY = "R171_LEGACY_TO_V2_GRAPH/v1"
V1_SCHEMA = "CreativeSession/v1"

_SAFE_SLOT_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")

_V2_INITIAL = StoryState(
    scene_id="archive_gate",
    beat_id="arrival",
    relationships={"mira": 0},
)

_V2_GRAPH: dict[tuple[str, str], dict[str, dict[str, Any]]] = {
    ("archive_gate", "arrival"): {
        "listen": {
            "transition_id": "gate_listen",
            "label": "Listen at the archive gate",
            "patch": {
                "beat_id": "echo",
                "reveal_facts": ["a witness is inside"],
                "risk_delta": 1,
            },
        },
        "knock": {
            "transition_id": "gate_knock",
            "label": "Knock and enter carefully",
            "patch": {
                "scene_id": "interior_archive",
                "beat_id": "threshold",
                "relationship_delta": {"mira": 1},
                "flags": {"arrival": "announced"},
            },
        },
        "defer": {
            "transition_id": "gate_defer",
            "label": "Defer until daylight",
            "patch": {
                "scene_id": "dawn_courtyard",
                "beat_id": "return",
                "risk_delta": -1,
                "flags": {"arrival": "deferred"},
            },
        },
    },
    ("archive_gate", "echo"): {
        "knock": {
            "transition_id": "echo_knock",
            "label": "Knock after hearing the witness",
            "patch": {
                "scene_id": "interior_archive",
                "beat_id": "threshold",
                "relationship_delta": {"mira": 1},
                "flags": {"clue": "heard"},
            },
        },
        "record": {
            "transition_id": "echo_record",
            "label": "Record the clue and withdraw",
            "patch": {
                "scene_id": "dawn_courtyard",
                "beat_id": "return",
                "flags": {"clue": "recorded"},
            },
        },
    },
    ("interior_archive", "threshold"): {
        "promise": {
            "transition_id": "threshold_promise",
            "label": "Promise to listen before acting",
            "patch": {
                "beat_id": "accord",
                "relationship_delta": {"mira": 1},
                "risk_delta": -1,
            },
        },
        "retreat": {
            "transition_id": "threshold_retreat",
            "label": "Retreat to a safe daylight meeting",
            "patch": {
                "scene_id": "dawn_courtyard",
                "beat_id": "return",
                "flags": {"meeting": "offered"},
            },
        },
    },
}

_V2_NARRATIVE = {
    ("archive_gate", "arrival"): "The archive gate holds the group at a clear decision point.",
    ("archive_gate", "echo"): "A witness can be heard beyond the gate.",
    ("interior_archive", "threshold"): "Inside the archive, the witness asks for a safe next step.",
    ("interior_archive", "accord"): "The group reaches an accord and preserves the record.",
    ("dawn_courtyard", "return"): "The group returns to the courtyard and keeps the case intact.",
}

# Frozen historic v1 semantics are used only to authenticate migration source evidence.
# They are not the authority for current-v2 continuation.
_LEGACY_GRAPH: dict[str, dict[str, Mapping[str, Any]]] = {
    "arrival": {
        "listen": {
            "beat_id": "echo",
            "reveal_facts": ["a witness is inside"],
            "risk_delta": 1,
        },
        "approach": {
            "beat_id": "threshold",
            "relationship_delta": {"mira": 1},
            "flags": {"arrival": "announced"},
        },
        "leave": {
            "beat_id": "courtyard",
            "risk_delta": -1,
            "flags": {"arrival": "deferred"},
        },
    },
    "echo": {
        "approach": {
            "beat_id": "threshold",
            "relationship_delta": {"mira": 1},
        },
        "leave": {
            "beat_id": "courtyard",
            "flags": {"clue": "recorded"},
        },
    },
    "threshold": {
        "listen": {
            "beat_id": "resolution",
            "relationship_delta": {"mira": 1},
            "risk_delta": -1,
        },
        "leave": {
            "beat_id": "courtyard",
            "flags": {"meeting": "offered"},
        },
    },
}

_LEGACY_TO_V2 = {
    ("arrival", "listen"): "listen",
    ("arrival", "approach"): "knock",
    ("arrival", "leave"): "defer",
    ("echo", "approach"): "knock",
    ("echo", "leave"): "record",
    ("threshold", "listen"): "promise",
    ("threshold", "leave"): "retreat",
}


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _source_path(workspace: Path) -> Path:
    return workspace / "session.json"


def _default_path(workspace: Path) -> Path:
    return workspace / "saves" / "default.json"


def _slot_path(workspace: Path, name: str) -> Path:
    if not name or any(char not in _SAFE_SLOT_CHARS for char in name):
        raise LedgerViolation("Unsafe save slot")
    return workspace / "saves" / "slots" / f"{name}.json"


def has_default(workspace: Path) -> bool:
    return _default_path(workspace).is_file()


def _graph_move(state: StoryState, action_id: str) -> tuple[dict[str, Any], StoryState]:
    transition = _V2_GRAPH.get((state.scene_id, state.beat_id), {}).get(action_id)
    if transition is None:
        raise LedgerViolation("Action is not legal in the current v2 state")
    patch = dict(transition["patch"])
    return transition, apply_state_patch(state, patch)


def legal_actions_for_state(state: StoryState) -> tuple[str, ...]:
    return tuple(sorted(_V2_GRAPH.get((state.scene_id, state.beat_id), {})))


def action_label(state: StoryState, action_id: str) -> str:
    transition = _V2_GRAPH.get((state.scene_id, state.beat_id), {}).get(action_id)
    if transition is None:
        raise LedgerViolation("Action is not legal in the current v2 state")
    return str(transition["label"])


def _story_effect(state: StoryState) -> tuple[Any, ...]:
    return (
        dict(state.relationships),
        tuple(state.known_facts),
        state.risk_level,
        dict(state.flags),
    )


def _legacy_source(raw: bytes) -> tuple[CreativeLedger, list[tuple[Any, StoryState, str, StoryState]]]:
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LedgerViolation("Legacy source is not valid UTF-8 JSON") from error
    if not isinstance(envelope, Mapping) or envelope.get("schema") != V1_SCHEMA:
        raise LedgerViolation("Legacy source schema is unsupported")
    records = envelope.get("events")
    if not isinstance(records, list):
        raise LedgerViolation("Legacy source events are malformed")
    ledger = CreativeLedger.from_records(records)
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise LedgerViolation("Legacy source has no canonical initializer")
    initial_payload = ledger.events[0].payload.get("state")
    if not isinstance(initial_payload, Mapping):
        raise LedgerViolation("Legacy initializer state is malformed")
    state = StoryState.from_dict(initial_payload)
    expected_initial = StoryState(
        scene_id="synthetic_archive",
        beat_id="arrival",
        relationships={"mira": 0},
    )
    if state != expected_initial:
        raise LedgerViolation("Legacy source starts outside the canonical v1 fixture")

    steps: list[tuple[Any, StoryState, str, StoryState]] = []
    for event in ledger.events[1:]:
        if event.event_type != "player_action":
            raise LedgerViolation("Legacy source contains a non-player event")
        action_data = event.payload.get("action")
        patch = event.payload.get("resulting_patch")
        if not isinstance(action_data, Mapping) or not isinstance(patch, Mapping):
            raise LedgerViolation("Legacy player action payload is malformed")
        action_id = str(action_data.get("action_id") or "")
        expected_patch = _LEGACY_GRAPH.get(state.beat_id, {}).get(action_id)
        if expected_patch is None:
            raise LedgerViolation("Legacy source contains an unknown historic route")
        if dict(patch) != dict(expected_patch):
            raise LedgerViolation("Legacy patch differs from frozen historic semantics")
        next_state = apply_state_patch(state, expected_patch)
        steps.append((event, state, action_id, next_state))
        state = next_state
    return ledger, steps


def _new_v2_ledger(*, occurred_at: str = "2030-01-01T00:00:00Z") -> CreativeLedger:
    ledger = CreativeLedger()
    ledger.append("story_initialized", {"state": _V2_INITIAL.to_dict()}, occurred_at)
    return ledger


def _append_graph_action(
    ledger: CreativeLedger,
    state: StoryState,
    action_id: str,
    *,
    occurred_at: str,
    source_text: str | None = None,
    migration_source: Mapping[str, Any] | None = None,
) -> StoryState:
    transition, next_state = _graph_move(state, action_id)
    payload: dict[str, Any] = {
        "action": PlayerAction(
            action_id=action_id,
            kind="choice",
            text=source_text or str(transition["label"]),
        ).to_dict(),
        "transition_id": str(transition["transition_id"]),
        "resulting_patch": dict(transition["patch"]),
    }
    if migration_source is not None:
        payload["migration_source"] = dict(migration_source)
    ledger.append("player_action", payload, occurred_at)
    return next_state


def _derive_migration(raw: bytes) -> tuple[dict[str, Any], CreativeLedger]:
    legacy_ledger, legacy_steps = _legacy_source(raw)
    initial_time = legacy_ledger.events[0].occurred_at
    v2_ledger = _new_v2_ledger(occurred_at=initial_time)
    v2_state = _V2_INITIAL
    legacy_final = StoryState.from_dict(legacy_ledger.events[0].payload["state"])

    for source_event, legacy_before, legacy_action, legacy_after in legacy_steps:
        mapped = _LEGACY_TO_V2.get((legacy_before.beat_id, legacy_action))
        if mapped is None:
            raise LedgerViolation("Legacy action has no governed v2 mapping")
        v2_state = _append_graph_action(
            v2_ledger,
            v2_state,
            mapped,
            occurred_at=source_event.occurred_at,
            source_text=str(source_event.payload.get("action", {}).get("text") or mapped),
            migration_source={
                "source_sequence": source_event.sequence,
                "source_event_id": source_event.event_id,
                "source_event_hash": source_event.event_hash,
                "legacy_action_id": legacy_action,
            },
        )
        if _story_effect(v2_state) != _story_effect(legacy_after):
            raise LedgerViolation("Legacy route is lossy under the governed v2 SceneGraph")
        legacy_final = legacy_after

    source_digest = _sha_bytes(raw)
    if legacy_final.beat_id == "resolution":
        v2_ledger.append(
            "migration_bridge",
            {
                "kind": "legacy_terminal_resolution_equivalence",
                "source_digest": source_digest,
                "source_terminal": {
                    "scene_id": legacy_final.scene_id,
                    "beat_id": legacy_final.beat_id,
                },
                "v2_terminal": {
                    "scene_id": v2_state.scene_id,
                    "beat_id": v2_state.beat_id,
                },
                "state_neutral": True,
            },
            f"2030-01-01T00:{len(v2_ledger.events):02d}:30Z",
        )

    bridge_positions = [
        {"sequence": event.sequence, "event_id": event.event_id}
        for event in v2_ledger.events
        if event.event_type == "migration_bridge"
    ]
    receipt = {
        "schema": MIGRATION_SCHEMA,
        "mapping_policy": MAPPING_POLICY,
        "source_digest": source_digest,
        "source_events_digest": _sha_value(legacy_ledger.to_records()),
        "source_event_count": len(legacy_ledger.events),
        "migrated_prefix_event_count": len(v2_ledger.events),
        "migration_bridge_positions": bridge_positions,
    }
    return receipt, v2_ledger


def _replay_authoritative(ledger: CreativeLedger) -> tuple[StoryState, list[dict[str, Any]]]:
    ledger.verify_chain()
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise LedgerViolation("CreativeSession/v2 must start with story_initialized")
    first_state = ledger.events[0].payload.get("state")
    if not isinstance(first_state, Mapping) or StoryState.from_dict(first_state) != _V2_INITIAL:
        raise LedgerViolation("CreativeSession/v2 initializer differs from SceneGraph authority")

    state = _V2_INITIAL
    timeline: list[dict[str, Any]] = [
        {
            "sequence": ledger.events[0].sequence,
            "event_id": ledger.events[0].event_id,
            "event_type": ledger.events[0].event_type,
            "state": state.to_dict(),
        }
    ]
    for event in ledger.events[1:]:
        if event.event_type == "state_patch":
            raise LedgerViolation("state_patch is forbidden in CreativeSession/v2")
        if event.event_type == "migration_bridge":
            if event.payload.get("state_neutral") is not True:
                raise LedgerViolation("migration_bridge must be state neutral")
        elif event.event_type == "player_action":
            action_data = event.payload.get("action")
            if not isinstance(action_data, Mapping):
                raise LedgerViolation("Saved v2 action is malformed")
            action_id = str(action_data.get("action_id") or "")
            transition, next_state = _graph_move(state, action_id)
            if event.payload.get("transition_id") != transition["transition_id"]:
                raise LedgerViolation("Saved v2 transition id disagrees with SceneGraph authority")
            patch = event.payload.get("resulting_patch")
            if not isinstance(patch, Mapping) or dict(patch) != dict(transition["patch"]):
                raise LedgerViolation("Saved v2 patch disagrees with SceneGraph authority")
            state = next_state
        else:
            raise LedgerViolation("CreativeSession/v2 contains a forbidden event type")
        timeline.append(
            {
                "sequence": event.sequence,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "state": state.to_dict(),
            }
        )
    return state, timeline


@dataclass
class ValidatedSession:
    ledger: CreativeLedger
    migration: Mapping[str, Any] | None
    legacy_source_path: Path | None = None

    @property
    def migrated(self) -> bool:
        return self.migration is not None

    def validate(self) -> StoryState:
        expected_prefix_length = 0
        if self.migration is not None:
            if self.legacy_source_path is None or not self.legacy_source_path.is_file():
                raise LedgerViolation("Migrated session requires immutable legacy source")
            raw = self.legacy_source_path.read_bytes()
            expected_receipt, expected_ledger = _derive_migration(raw)
            if dict(self.migration) != expected_receipt:
                raise LedgerViolation("Migration receipt does not bind to immutable legacy source")
            expected_records = expected_ledger.to_records()
            actual_records = self.ledger.to_records()
            expected_prefix_length = len(expected_records)
            if actual_records[:expected_prefix_length] != expected_records:
                raise LedgerViolation("Migrated v2 ledger prefix differs from immutable source reconstruction")
            expected_bridges = [
                (event.sequence, event.event_id)
                for event in expected_ledger.events
                if event.event_type == "migration_bridge"
            ]
            actual_bridges = [
                (event.sequence, event.event_id)
                for event in self.ledger.events
                if event.event_type == "migration_bridge"
            ]
            if actual_bridges != expected_bridges:
                raise LedgerViolation("Migration bridge positions and identities differ from source reconstruction")
        else:
            if any(event.event_type == "migration_bridge" for event in self.ledger.events):
                raise LedgerViolation("Native v2 session may not contain a migration bridge")

        for event in self.ledger.events[expected_prefix_length:]:
            if event.event_type == "migration_bridge":
                raise LedgerViolation("Continuation may not mint a migration bridge")
            if event.event_type == "player_action" and "migration_source" in event.payload:
                raise LedgerViolation("Continuation may not mint migration source provenance")
        state, _ = _replay_authoritative(self.ledger)
        return state

    def state(self) -> StoryState:
        return self.validate()

    def timeline(self) -> dict[str, Any]:
        final_state = self.validate()
        replayed_state, events = _replay_authoritative(self.ledger)
        if replayed_state != final_state:
            raise LedgerViolation("Timeline state diverges from validated session state")
        return {
            "schema": "CreativeTimeline/v1",
            "migrated": self.migrated,
            "event_history_digest": _sha_value(self.ledger.to_records()),
            "events": events,
            "final_state": final_state.to_dict(),
        }

    def director_sequence(self) -> dict[str, Any]:
        timeline = self.timeline()
        packets = []
        for entry in timeline["events"]:
            state = StoryState.from_dict(entry["state"])
            compiled = compile_director(state)
            packets.append(
                {
                    "event_sequence": entry["sequence"],
                    "event_id": entry["event_id"],
                    "state": state.to_dict(),
                    "brief": compiled.brief.to_dict(),
                    "shots": [shot.to_dict() for shot in compiled.shots],
                    "quality_report": compiled.quality_report.to_dict(),
                }
            )
        if packets and packets[-1]["state"] != timeline["final_state"]:
            raise LedgerViolation("Director sequence final state diverges from timeline")
        return {
            "schema": "DirectorSequence/v1",
            "migrated": self.migrated,
            "event_history_digest": timeline["event_history_digest"],
            "packets": packets,
            "final_state": timeline["final_state"],
        }

    def review_packet(self) -> dict[str, Any]:
        final_state = self.state()
        timeline = self.timeline()
        director = self.director_sequence()
        if timeline["final_state"] != final_state.to_dict():
            raise LedgerViolation("Review packet timeline state mismatch")
        if director["final_state"] != final_state.to_dict():
            raise LedgerViolation("Review packet director state mismatch")
        packet = {
            "schema": "CreativeReviewPacket/v1",
            "migrated": self.migrated,
            "migration": dict(self.migration) if self.migration is not None else None,
            "event_history_digest": _sha_value(self.ledger.to_records()),
            "event_count": len(self.ledger.events),
            "final_state": final_state.to_dict(),
            "timeline_digest": _sha_value(timeline),
            "director_sequence_digest": _sha_value(director),
            "canonical_knowledge_written": False,
            "generation_called": False,
        }
        packet["packet_digest"] = _sha_value(packet)
        return packet


class SessionStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)

    def path(self, slot: str | None = None) -> Path:
        return _slot_path(self.workspace, slot) if slot is not None else _default_path(self.workspace)

    def read(self, slot: str | None = None) -> ValidatedSession:
        path = self.path(slot)
        if not path.is_file():
            raise LedgerViolation("No CreativeSession/v2 save exists")
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise LedgerViolation("Saved v2 session is not valid JSON") from error
        if not isinstance(envelope, Mapping) or envelope.get("schema") != SCHEMA:
            raise LedgerViolation("Saved session schema is unsupported")
        events = envelope.get("events")
        if not isinstance(events, list):
            raise LedgerViolation("Saved v2 events are malformed")
        migration = envelope.get("migration")
        if migration is not None and not isinstance(migration, Mapping):
            raise LedgerViolation("Saved migration receipt is malformed")
        session = ValidatedSession(
            ledger=CreativeLedger.from_records(events),
            migration=dict(migration) if migration is not None else None,
            legacy_source_path=_source_path(self.workspace) if migration is not None else None,
        )
        session.validate()
        return session

    def write(self, session: ValidatedSession, slot: str | None = None) -> None:
        session.validate()
        path = self.path(slot)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "schema": SCHEMA,
            "events": session.ledger.to_records(),
            "migration": dict(session.migration) if session.migration is not None else None,
        }
        path.write_text(canonical_json(envelope) + "\n", encoding="utf-8")


def migrate(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    store = SessionStore(workspace)
    if store.path().exists():
        session = store.read()
        if not session.migrated:
            raise LedgerViolation("Existing native v2 save cannot be relabeled as migrated")
        return {
            "schema": SCHEMA,
            "events": session.ledger.to_records(),
            "migration": dict(session.migration or {}),
        }
    source = _source_path(workspace)
    if not source.is_file():
        raise LedgerViolation("No legacy session exists to migrate")
    original = source.read_bytes()
    receipt, ledger = _derive_migration(original)
    session = ValidatedSession(ledger, receipt, source)
    session.validate()
    store.write(session)
    if source.read_bytes() != original:
        raise LedgerViolation("Legacy source bytes changed during migration")
    return {
        "schema": SCHEMA,
        "events": ledger.to_records(),
        "migration": dict(receipt),
    }


def initialize_native(workspace: Path) -> ValidatedSession:
    workspace = Path(workspace)
    store = SessionStore(workspace)
    if store.path().exists():
        return store.read()
    session = ValidatedSession(_new_v2_ledger(), None, None)
    store.write(session)
    return session


def load_session(workspace: Path, slot: str | None = None) -> ValidatedSession:
    return SessionStore(Path(workspace)).read(slot)


def load(workspace: Path, slot: str | None = None) -> tuple[dict[str, Any], StoryState]:
    session = load_session(workspace, slot)
    envelope = {
        "schema": SCHEMA,
        "events": session.ledger.to_records(),
        "migration": dict(session.migration) if session.migration is not None else None,
    }
    return envelope, session.state()


def state(workspace: Path, slot: str | None = None) -> StoryState:
    return load_session(workspace, slot).state()


def legal_actions(workspace: Path, slot: str | None = None) -> tuple[str, ...]:
    return legal_actions_for_state(state(workspace, slot))


def choose(workspace: Path, action_id: str, source_text: str | None = None) -> StoryState:
    workspace = Path(workspace)
    store = SessionStore(workspace)
    session = store.read()
    current = session.state()
    occurred_at = f"2030-01-02T00:{len(session.ledger.events):02d}:00Z"
    next_state = _append_graph_action(
        session.ledger,
        current,
        action_id,
        occurred_at=occurred_at,
        source_text=source_text,
    )
    session.validate()
    store.write(session)
    return next_state


def save_default(workspace: Path) -> None:
    workspace = Path(workspace)
    store = SessionStore(workspace)
    store.write(store.read())


def save_slot(workspace: Path, name: str) -> None:
    workspace = Path(workspace)
    store = SessionStore(workspace)
    store.write(store.read(), name)


def restore_slot(workspace: Path, name: str) -> StoryState:
    workspace = Path(workspace)
    store = SessionStore(workspace)
    session = store.read(name)
    store.write(session)
    return session.state()


def timeline(workspace: Path, slot: str | None = None) -> dict[str, Any]:
    return load_session(workspace, slot).timeline()


def director_sequence(workspace: Path, slot: str | None = None) -> dict[str, Any]:
    return load_session(workspace, slot).director_sequence()


def review_packet(workspace: Path, slot: str | None = None) -> dict[str, Any]:
    return load_session(workspace, slot).review_packet()


def view(workspace: Path) -> dict[str, Any]:
    session = load_session(workspace)
    current = session.state()
    actions = legal_actions_for_state(current)
    return {
        "status": "ready",
        "v2": True,
        "migrated": session.migrated,
        "state": current.to_dict(),
        "text": _V2_NARRATIVE.get(
            (current.scene_id, current.beat_id),
            "The deterministic scene has reached a stable endpoint.",
        ),
        "options": [
            {"id": action_id, "label": action_label(current, action_id)}
            for action_id in actions
        ],
        "event_count": len(session.ledger.events),
    }
