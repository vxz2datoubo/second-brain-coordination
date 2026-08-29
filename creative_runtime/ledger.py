"""Append-only, deterministic story event storage for offline replay."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from .contracts import CreativeArtifact, CreativeEvent, StoryState, canonical_json


class LedgerViolation(ValueError):
    """Raised for invalid events, corrupted chains, or non-replayable state."""


def digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _event_material(
    *, sequence: int, event_type: str, occurred_at: str, payload: Mapping[str, Any],
    previous_hash: str | None, parent_artifact_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "CreativeEvent/v1",
        "sequence": sequence,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "payload": payload,
        "previous_hash": previous_hash,
        "parent_artifact_ids": list(parent_artifact_ids),
    }


def create_artifact(
    artifact_type: str,
    content: Mapping[str, Any],
    created_at: str,
    parent_artifact_ids: Iterable[str] = (),
    provenance_class: str = "private_adaptation",
) -> CreativeArtifact:
    """Create a stable artifact identifier from explicit, replayable inputs."""

    parents = tuple(parent_artifact_ids)
    source_hash = digest({"artifact_type": artifact_type, "content": dict(content), "parents": list(parents)})
    return CreativeArtifact(
        artifact_id="art_" + source_hash[:20],
        artifact_type=artifact_type,
        content=dict(content),
        source_hash=source_hash,
        created_at=created_at,
        parent_artifact_ids=parents,
        provenance_class=provenance_class,
    )


def apply_state_patch(state: StoryState, patch: Mapping[str, Any]) -> StoryState:
    """Apply the deliberately small patch language used by interactive beats."""

    unknown = set(patch) - {"scene_id", "beat_id", "relationship_delta", "reveal_facts", "risk_delta", "flags"}
    if unknown:
        raise LedgerViolation("Unsupported state patch fields: " + ", ".join(sorted(unknown)))
    relationships = dict(state.relationships)
    for person, delta in patch.get("relationship_delta", {}).items():
        relationships[str(person)] = relationships.get(str(person), 0) + int(delta)
    known_facts = list(state.known_facts)
    for fact in patch.get("reveal_facts", []):
        fact = str(fact)
        if fact not in known_facts:
            known_facts.append(fact)
    flags = dict(state.flags)
    flags.update({str(key): str(value) for key, value in patch.get("flags", {}).items()})
    return StoryState(
        scene_id=str(patch.get("scene_id", state.scene_id)),
        beat_id=str(patch.get("beat_id", state.beat_id)),
        relationships=relationships,
        known_facts=tuple(known_facts),
        risk_level=state.risk_level + int(patch.get("risk_delta", 0)),
        flags=flags,
    )


@dataclass
class CreativeLedger:
    """Memory-only ledger that can be serialized and verified in any clean clone."""

    events: list[CreativeEvent]

    def __init__(self, events: Iterable[CreativeEvent] = ()) -> None:
        self.events = list(events)
        self.verify_chain()

    def append(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        occurred_at: str,
        parent_artifact_ids: Iterable[str] = (),
    ) -> CreativeEvent:
        if event_type not in {"story_initialized", "player_action", "state_patch"}:
            raise LedgerViolation("Unsupported event type: " + event_type)
        sequence = len(self.events)
        previous_hash = self.events[-1].event_hash if self.events else None
        parents = tuple(parent_artifact_ids)
        material = _event_material(
            sequence=sequence,
            event_type=event_type,
            occurred_at=occurred_at,
            payload=dict(payload),
            previous_hash=previous_hash,
            parent_artifact_ids=parents,
        )
        event_hash = digest(material)
        event = CreativeEvent(
            event_id="evt_" + event_hash[:20],
            sequence=sequence,
            event_type=event_type,
            occurred_at=occurred_at,
            payload=dict(payload),
            previous_hash=previous_hash,
            event_hash=event_hash,
            parent_artifact_ids=parents,
        )
        self.events.append(event)
        return event

    def replay(self) -> StoryState:
        self.verify_chain()
        if not self.events or self.events[0].event_type != "story_initialized":
            raise LedgerViolation("A ledger must start with story_initialized")
        state = StoryState.from_dict(self.events[0].payload["state"])
        for event in self.events[1:]:
            if event.event_type == "player_action":
                patch = event.payload.get("resulting_patch")
                if not isinstance(patch, Mapping):
                    raise LedgerViolation("player_action requires a resulting_patch")
                state = apply_state_patch(state, patch)
            elif event.event_type == "state_patch":
                patch = event.payload.get("patch")
                if not isinstance(patch, Mapping):
                    raise LedgerViolation("state_patch requires a patch")
                state = apply_state_patch(state, patch)
            else:
                raise LedgerViolation("story_initialized may only appear first")
        return state

    def verify_chain(self) -> None:
        previous_hash: str | None = None
        for expected_sequence, event in enumerate(self.events):
            if event.sequence != expected_sequence:
                raise LedgerViolation("Event sequence is not contiguous")
            material = _event_material(
                sequence=event.sequence,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                payload=event.payload,
                previous_hash=previous_hash,
                parent_artifact_ids=event.parent_artifact_ids,
            )
            expected_hash = digest(material)
            if event.previous_hash != previous_hash or event.event_hash != expected_hash:
                raise LedgerViolation("Event chain hash mismatch at " + event.event_id)
            if event.event_id != "evt_" + expected_hash[:20]:
                raise LedgerViolation("Event identifier mismatch at sequence " + str(event.sequence))
            previous_hash = event.event_hash

    def to_records(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]

    @classmethod
    def from_records(cls, records: Iterable[Mapping[str, Any]]) -> "CreativeLedger":
        return cls(
            CreativeEvent(
                event_id=str(record["event_id"]),
                sequence=int(record["sequence"]),
                event_type=str(record["event_type"]),
                occurred_at=str(record["occurred_at"]),
                payload=dict(record["payload"]),
                previous_hash=record.get("previous_hash"),
                event_hash=str(record["event_hash"]),
                parent_artifact_ids=tuple(record.get("parent_artifact_ids", ())),
            )
            for record in records
        )
