"""Versioned, root-confined save slots with audited canonical-v1 migration."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

from .contracts import StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation, apply_state_patch
from .scene_graph import SceneGraph, SceneGraphViolation, synthetic_three_scene_manifest


CURRENT_SESSION_SCHEMA = "CreativeSession/v2"
LEGACY_SESSION_SCHEMA = "CreativeSession/v1"
CANONICAL_LEGACY_BASELINE = "027642a231e214f8649b273f44de65c82a4901f9"
_SLOT = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{number}" for number in range(1, 10)), *(f"lpt{number}" for number in range(1, 10))}


class SaveSlotViolation(ValueError):
    """Raised for unsafe paths, malformed sessions, or unsupported migration."""


@dataclass(frozen=True)
class LoadedSession:
    ledger: CreativeLedger
    manifest_hash: str
    schema: str
    migrations: tuple[str, ...] = ()
    migration_receipt: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class _LegacyRule:
    expected_patch: Mapping[str, Any]
    new_action_id: str


_LEGACY_RULES: dict[tuple[str, str], _LegacyRule] = {
    ("arrival", "listen"): _LegacyRule({"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}, "listen"),
    ("arrival", "approach"): _LegacyRule({"beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}, "knock"),
    ("arrival", "leave"): _LegacyRule({"beat_id": "courtyard", "risk_delta": -1, "flags": {"arrival": "deferred"}}, "defer"),
    ("echo", "approach"): _LegacyRule({"beat_id": "threshold", "relationship_delta": {"mira": 1}}, "knock"),
    ("echo", "leave"): _LegacyRule({"beat_id": "courtyard", "flags": {"clue": "recorded"}}, "record"),
    ("threshold", "listen"): _LegacyRule({"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1}, "promise"),
    ("threshold", "leave"): _LegacyRule({"beat_id": "courtyard", "flags": {"meeting": "offered"}}, "retreat"),
}


def _same_story_semantics(left: StoryState, right: StoryState) -> bool:
    return (
        dict(left.relationships) == dict(right.relationships)
        and tuple(left.known_facts) == tuple(right.known_facts)
        and left.risk_level == right.risk_level
        and dict(left.flags) == dict(right.flags)
    )


def _migrate_legacy_v1(record: Mapping[str, Any], graph: SceneGraph) -> tuple[dict[str, Any], tuple[str, ...]]:
    events = record.get("events")
    if not isinstance(events, list):
        raise SaveSlotViolation("Legacy session has no event list")
    try:
        legacy_ledger = CreativeLedger.from_records(events)
    except (KeyError, LedgerViolation, TypeError, ValueError) as error:
        raise SaveSlotViolation("Legacy event chain is corrupt or non-replayable") from error
    if not legacy_ledger.events or legacy_ledger.events[0].event_type != "story_initialized":
        raise SaveSlotViolation("Legacy session must start with story_initialized")

    try:
        legacy_state = StoryState.from_dict(legacy_ledger.events[0].payload["state"])
    except (KeyError, TypeError, ValueError) as error:
        raise SaveSlotViolation("Legacy initial state is malformed") from error
    if (legacy_state.scene_id, legacy_state.beat_id) != ("synthetic_archive", "arrival"):
        raise SaveSlotViolation("Legacy session is not the canonical S00-S06 synthetic_archive format")

    new_ledger = CreativeLedger()
    new_state = graph.initial_state()
    new_ledger.append(
        "story_initialized",
        {"state": new_state.to_dict()},
        legacy_ledger.events[0].occurred_at,
        legacy_ledger.events[0].parent_artifact_ids,
    )
    mappings: list[dict[str, Any]] = []

    for legacy_event in legacy_ledger.events[1:]:
        if legacy_event.event_type != "player_action":
            raise SaveSlotViolation("Canonical S00-S06 legacy sessions may contain only player_action after initialization")
        action = legacy_event.payload.get("action")
        patch = legacy_event.payload.get("resulting_patch")
        if not isinstance(action, Mapping) or not isinstance(patch, Mapping):
            raise SaveSlotViolation("Legacy player_action is malformed")
        action_id = str(action.get("action_id", ""))
        rule = _LEGACY_RULES.get((legacy_state.beat_id, action_id))
        if rule is None:
            raise SaveSlotViolation(f"Legacy action cannot be mapped losslessly: {legacy_state.beat_id}/{action_id}")
        if canonical_json(dict(patch)) != canonical_json(dict(rule.expected_patch)):
            raise SaveSlotViolation(f"Legacy patch differs from canonical S00-S06 semantics at {legacy_state.beat_id}/{action_id}")

        try:
            next_legacy_state = apply_state_patch(legacy_state, patch)
            next_new_state, graph_action = graph.apply(new_state, rule.new_action_id)
        except (LedgerViolation, SceneGraphViolation) as error:
            raise SaveSlotViolation("Legacy transition cannot be represented by the current scene graph") from error
        if not _same_story_semantics(next_legacy_state, next_new_state):
            raise SaveSlotViolation(f"Legacy consequences cannot be preserved losslessly at {legacy_state.beat_id}/{action_id}")

        mapped_action = {
            "action_id": graph_action.action_id,
            "kind": str(action.get("kind", "choice")),
            "text": str(action.get("text", graph_action.label)),
            "confidence": float(action.get("confidence", 1.0)),
        }
        resulting_patch = {**dict(graph_action.patch), "scene_id": next_new_state.scene_id, "beat_id": next_new_state.beat_id}
        new_event = new_ledger.append(
            "player_action",
            {
                "action": mapped_action,
                "transition_id": graph_action.transition_id,
                "resulting_patch": resulting_patch,
                "migration_source": {
                    "legacy_event_id": legacy_event.event_id,
                    "legacy_scene_id": legacy_state.scene_id,
                    "legacy_beat_id": legacy_state.beat_id,
                    "legacy_action_id": action_id,
                },
            },
            legacy_event.occurred_at,
            legacy_event.parent_artifact_ids,
        )
        mappings.append({
            "legacy_event_id": legacy_event.event_id,
            "legacy_beat_id": legacy_state.beat_id,
            "legacy_action_id": action_id,
            "new_event_id": new_event.event_id,
            "new_scene_id": next_new_state.scene_id,
            "new_beat_id": next_new_state.beat_id,
            "new_action_id": graph_action.action_id,
        })
        legacy_state = next_legacy_state
        new_state = next_new_state

    terminal_mapping: dict[str, Any] | None = None
    if legacy_state.beat_id == "resolution":
        terminal_event = new_ledger.append(
            "state_patch",
            {"patch": {"scene_id": "dawn_courtyard", "beat_id": "return"}, "migration_reason": "legacy_resolution_terminal_equivalence"},
            legacy_ledger.events[-1].occurred_at,
        )
        new_state = new_ledger.replay()
        if not _same_story_semantics(legacy_state, new_state):
            raise SaveSlotViolation("Legacy resolution terminal mapping changed story consequences")
        terminal_mapping = {
            "legacy_scene_id": "synthetic_archive",
            "legacy_beat_id": "resolution",
            "new_scene_id": "dawn_courtyard",
            "new_beat_id": "return",
            "new_event_id": terminal_event.event_id,
            "method": "explicit_terminal_state_patch_after_promise",
        }

    if legacy_state.beat_id == "courtyard" and (new_state.scene_id, new_state.beat_id) != ("dawn_courtyard", "return"):
        raise SaveSlotViolation("Legacy courtyard terminal did not map to dawn_courtyard/return")
    if legacy_state.beat_id not in {"arrival", "echo", "threshold", "courtyard", "resolution"}:
        raise SaveSlotViolation("Legacy final beat is not a canonical S00-S06 beat")

    source_digest = hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()
    receipt = {
        "schema": "CreativeSessionMigrationReceipt/v1",
        "source_schema": LEGACY_SESSION_SCHEMA,
        "target_schema": CURRENT_SESSION_SCHEMA,
        "source_baseline": CANONICAL_LEGACY_BASELINE,
        "source_record_sha256": source_digest,
        "mapping_policy": "EXPLICIT_CANONICAL_S00_S06_TO_THREE_SCENE_GRAPH",
        "event_mappings": mappings,
        "terminal_mapping": terminal_mapping,
        "legacy_final_state": legacy_state.to_dict(),
        "migrated_final_state": new_state.to_dict(),
        "semantic_fields_preserved": ["relationships", "known_facts", "risk_level", "flags"],
    }
    migrated = {
        "schema": CURRENT_SESSION_SCHEMA,
        "manifest_hash": graph.manifest_hash,
        "events": new_ledger.to_records(),
        "migration_history": ["CreativeSession/v1->v2:r163-canonical-semantic-mapping"],
        "migration_receipt": receipt,
    }
    return migrated, ("CreativeSession/v1->v2:r163-canonical-semantic-mapping",)


def migrate_session(record: Mapping[str, Any], expected_manifest_hash: str, graph: SceneGraph | None = None) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Migrate only canonical S00-S06 v1 sessions; fail closed on semantic ambiguity."""

    schema = record.get("schema")
    if schema == CURRENT_SESSION_SCHEMA:
        migrated = dict(record)
        if migrated.get("manifest_hash") != expected_manifest_hash:
            raise SaveSlotViolation("Save manifest hash does not match the current graph")
        try:
            CreativeLedger.from_records(migrated.get("events", []))
        except (KeyError, LedgerViolation, TypeError, ValueError) as error:
            raise SaveSlotViolation("Save slot is corrupt or incompatible") from error
        return migrated, ()
    if schema != LEGACY_SESSION_SCHEMA:
        raise SaveSlotViolation("Unsupported session schema: " + str(schema))

    active_graph = graph or SceneGraph(synthetic_three_scene_manifest())
    if active_graph.manifest_hash != expected_manifest_hash:
        raise SaveSlotViolation("Migration graph does not match expected manifest hash")
    return _migrate_legacy_v1(record, active_graph)


class SaveStore:
    """Filesystem helper that confines every save operation to one configured root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _name(self, slot: str) -> str:
        normalized = str(slot).casefold()
        if not _SLOT.fullmatch(normalized) or normalized in _RESERVED:
            raise SaveSlotViolation("Invalid save slot name")
        return normalized

    def _path(self, slot: str) -> Path:
        name = self._name(slot)
        candidate = (self.root / f"{name}.json").resolve()
        if candidate.parent != self.root:
            raise SaveSlotViolation("Save slot escapes configured root")
        return candidate

    def list_slots(self) -> list[str]:
        if not self.root.exists():
            return []
        if not self.root.is_dir():
            raise SaveSlotViolation("Save root is not a directory")
        return sorted(path.stem for path in self.root.glob("*.json") if path.is_file() and _SLOT.fullmatch(path.stem))

    def _atomic_write(self, target: Path, payload: Mapping[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".save-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(canonical_json(payload) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, target)
        except OSError as error:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            finally:
                raise SaveSlotViolation("Save replacement failed") from error
        return target

    def save(self, slot: str, ledger: CreativeLedger, manifest_hash: str) -> Path:
        target = self._path(slot)
        payload = {"schema": CURRENT_SESSION_SCHEMA, "manifest_hash": manifest_hash, "events": ledger.to_records(), "migration_history": []}
        return self._atomic_write(target, payload)

    def save_record(self, slot: str, record: Mapping[str, Any], expected_manifest_hash: str) -> Path:
        target = self._path(slot)
        if record.get("schema") != CURRENT_SESSION_SCHEMA or record.get("manifest_hash") != expected_manifest_hash:
            raise SaveSlotViolation("Migrated save record is not bound to the current graph")
        try:
            CreativeLedger.from_records(record.get("events", []))
        except (KeyError, LedgerViolation, TypeError, ValueError) as error:
            raise SaveSlotViolation("Migrated save record has an invalid event chain") from error
        return self._atomic_write(target, record)

    def load(self, slot: str, expected_manifest_hash: str, graph: SceneGraph | None = None) -> LoadedSession:
        path = self._path(slot)
        if not path.is_file():
            raise SaveSlotViolation("Save slot does not exist")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, Mapping):
                raise SaveSlotViolation("Save payload must be an object")
            record, migrations = migrate_session(raw, expected_manifest_hash, graph)
            ledger = CreativeLedger.from_records(record["events"])
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, LedgerViolation, TypeError, ValueError) as error:
            raise SaveSlotViolation("Save slot is corrupt or incompatible") from error
        return LoadedSession(ledger=ledger, manifest_hash=expected_manifest_hash, schema=CURRENT_SESSION_SCHEMA, migrations=migrations, migration_receipt=record.get("migration_receipt"))

    def delete(self, slot: str) -> bool:
        path = self._path(slot)
        if not path.exists():
            return False
        if not path.is_file():
            raise SaveSlotViolation("Save slot path is not a file")
        path.unlink()
        return True
