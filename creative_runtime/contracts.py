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
class ChoiceIntent:
    intent_id: str
    campaign_id: str
    source_type: str
    normalized_choice_id: str | None
    confidence: float
    clarification_required: bool
    content_gate_status: str

    @property
    def schema(self) -> str:
        return "ChoiceIntent/v1"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


@dataclass(frozen=True)
class NarrativeProposal:
    proposal_id: str
    campaign_id: str
    based_on_state_hash: str
    choice_intent_id: str
    candidate_dialogue: tuple[str, ...]
    candidate_character_reactions: Mapping[str, str]
    candidate_beat_ids: tuple[str, ...]
    candidate_presentation: Mapping[str, str]
    model_or_simulator_ref: str
    policy_revision: str
    proposed_transition_id: str

    @property
    def schema(self) -> str:
        return "NarrativeProposal/v1"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


@dataclass(frozen=True)
class DramaticBeatSelection:
    selection_id: str
    campaign_id: str
    eligible_beat_ids: tuple[str, ...]
    selected_beat_id: str
    selection_reason: str
    preserved_player_facts_hash: str
    policy_revision: str

    @property
    def schema(self) -> str:
        return "DramaticBeatSelection/v1"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


@dataclass(frozen=True)
class QuestState:
    quest_id: str
    phase: str
    objectives: tuple[str, ...]
    pressure: int
    status: str

    @property
    def schema(self) -> str:
        return "QuestState/v1"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


@dataclass(frozen=True)
class RewardState:
    reward_id: str
    reward_type: str
    source_event_id: str
    mechanical_or_emotional_effect: str
    tradeoff: str

    @property
    def schema(self) -> str:
        return "RewardState/v1"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


@dataclass(frozen=True)
class RelationshipState:
    character_id: str
    trust: int
    conflict: int
    commitment: int
    known_by_character: tuple[str, ...]

    @property
    def schema(self) -> str:
        return "RelationshipState/v1"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


@dataclass(frozen=True)
class AntagonistState:
    antagonist_id: str
    objective: str
    secret_boundary: tuple[str, ...]
    pressure: int
    countermeasure: str
    status: str

    @property
    def schema(self) -> str:
        return "AntagonistState/v1"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


@dataclass(frozen=True)
class DirectorBrief:
    brief_id: str
    story_state: StoryState
    character_goals: Mapping[str, str]
    knowledge_boundaries: Mapping[str, tuple[str, ...]]
    spatial_facts: tuple[str, ...]
    content_rating: str = "non_explicit"
    activated_skill_ids: tuple[str, ...] = ()
    skill_trigger_reasons: Mapping[str, str] = field(default_factory=dict)
    source_timeline_hash: str | None = None
    story_consequence: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class ScriptPackage:
    """Immutable, approved content package for one replayable story graph."""

    script_id: str
    script_revision: str
    genre: tuple[str, ...]
    content_rating: str
    season_catalog: tuple[str, ...]
    chapter_catalog: tuple[str, ...]
    scene_catalog: tuple[str, ...]
    world_bible_ref: str
    character_bible_refs: tuple[str, ...]
    scene_bible_refs: tuple[str, ...]
    story_beats: tuple[str, ...]
    legal_choices: tuple[str, ...]
    consequence_rules: tuple[str, ...]
    reward_rules: tuple[str, ...]
    ending_rules: tuple[str, ...]
    style_profiles: tuple[str, ...]
    asset_manifest_ref: str
    source_provenance: str
    approval_status: str
    initial_state: StoryState
    graph_revision: str

    @property
    def schema(self) -> str:
        return "ScriptPackage/v1"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


@dataclass(frozen=True)
class DirectorBriefV2:
    """A director brief explicitly bound to a script, campaign, and style."""

    script_id: str
    script_revision: str
    campaign_id: str
    verified_story_state_hash: str
    style_profile_id: str
    cast_revision_ids: tuple[str, ...]
    scene_asset_refs: tuple[str, ...]
    continuity_ledger_hash: str
    director_policy_revision: str
    narrative_brief: DirectorBrief

    @property
    def schema(self) -> str:
        return "DirectorBrief/v2"

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, **_json_value(self)}


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
