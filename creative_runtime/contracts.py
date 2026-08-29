"""Stable, JSON-only contracts shared by the offline creative slices.

The contracts intentionally carry data rather than provider behavior. They can
be serialized, hashed, replayed and independently checked without credentials,
network access, media binaries, or a canonical knowledge-store write.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
import json
from typing import Any, Mapping


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Render a JSON value in the single format used for hashes and replay."""

    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@dataclass(frozen=True)
class StoryState:
    scene_id: str
    beat_id: str
    relationships: Mapping[str, int] = field(default_factory=dict)
    known_facts: tuple[str, ...] = ()
    risk_level: int = 0
    flags: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StoryState":
        return cls(
            scene_id=str(value["scene_id"]),
            beat_id=str(value["beat_id"]),
            relationships={str(k): int(v) for k, v in value.get("relationships", {}).items()},
            known_facts=tuple(str(item) for item in value.get("known_facts", [])),
            risk_level=int(value.get("risk_level", 0)),
            flags={str(k): str(v) for k, v in value.get("flags", {}).items()},
        )


@dataclass(frozen=True)
class StoryBeat:
    beat_id: str
    scene_id: str
    title: str
    objective: str
    legal_action_ids: tuple[str, ...]
    private_adaptation: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class PlayerAction:
    action_id: str
    kind: str
    text: str
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class DirectorBrief:
    brief_id: str
    story_state: StoryState
    character_goals: Mapping[str, str]
    knowledge_boundaries: Mapping[str, tuple[str, ...]]
    spatial_facts: tuple[str, ...]
    content_rating: str = "non_explicit"

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class ShotPlan:
    shot_id: str
    beat_id: str
    shot_role: str
    camera: str
    performance_task: str
    duration_seconds: int
    reference_artifact_ids: tuple[str, ...] = ()
    axis: str = ""
    lighting: str = ""
    sound: str = ""
    dominant_change: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class GenerationRequest:
    request_id: str
    provider: str
    shot_plan: ShotPlan
    content_rating: str
    confirm_generate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class GenerationResult:
    request_id: str
    provider: str
    status: str
    output_ref: str | None
    request_hash: str
    simulated: bool

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class CreativeArtifact:
    artifact_id: str
    artifact_type: str
    content: Mapping[str, Any]
    source_hash: str
    created_at: str
    parent_artifact_ids: tuple[str, ...] = ()
    provenance_class: str = "private_adaptation"

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class CreativeEvent:
    event_id: str
    sequence: int
    event_type: str
    occurred_at: str
    payload: Mapping[str, Any]
    previous_hash: str | None
    event_hash: str
    parent_artifact_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)
