"""Validated, deterministic scene graphs for the offline interactive-film game."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping

from .contracts import StoryState, canonical_json
from .ledger import LedgerViolation, apply_state_patch


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class SceneGraphViolation(ValueError):
    """Raised before an invalid manifest or transition can influence story state."""


@dataclass(frozen=True)
class GraphAction:
    action_id: str
    label: str
    transition_id: str
    target_scene_id: str
    target_beat_id: str
    patch: Mapping[str, Any]


@dataclass(frozen=True)
class GraphBeat:
    scene_id: str
    beat_id: str
    text: str
    recap: str
    actions: tuple[GraphAction, ...]


class SceneGraph:
    """An immutable manifest index with validated, explicit cross-scene edges."""

    def __init__(self, manifest: Mapping[str, Any]) -> None:
        self.manifest = dict(manifest)
        self._beats: dict[tuple[str, str], GraphBeat] = {}
        self._validate_and_index()
        self.manifest_hash = hashlib.sha256(canonical_json(self.manifest).encode("utf-8")).hexdigest()

    def _validate_identifier(self, value: Any, field: str) -> str:
        text = str(value)
        if not _IDENTIFIER.fullmatch(text):
            raise SceneGraphViolation(f"Invalid {field}: {text!r}")
        return text

    def _validate_and_index(self) -> None:
        if self.manifest.get("schema") != "SceneManifest/v1":
            raise SceneGraphViolation("Unsupported scene manifest schema")
        if self.manifest.get("content_rating") != "non_explicit" or self.manifest.get("adult_characters") is not True:
            raise SceneGraphViolation("Manifest must be adult-only and non_explicit")
        scenes = self.manifest.get("scenes")
        if not isinstance(scenes, list) or len(scenes) < 3:
            raise SceneGraphViolation("Manifest requires at least three scenes")
        scene_ids: set[str] = set()
        for scene in scenes:
            if not isinstance(scene, Mapping):
                raise SceneGraphViolation("Scene must be an object")
            scene_id = self._validate_identifier(scene.get("scene_id"), "scene_id")
            if scene_id in scene_ids:
                raise SceneGraphViolation("Duplicate scene_id: " + scene_id)
            scene_ids.add(scene_id)
            beats = scene.get("beats")
            if not isinstance(beats, list) or not beats:
                raise SceneGraphViolation("Every scene needs at least one beat")
            beat_ids: set[str] = set()
            for raw_beat in beats:
                if not isinstance(raw_beat, Mapping):
                    raise SceneGraphViolation("Beat must be an object")
                beat_id = self._validate_identifier(raw_beat.get("beat_id"), "beat_id")
                if beat_id in beat_ids or (scene_id, beat_id) in self._beats:
                    raise SceneGraphViolation(f"Duplicate beat: {scene_id}/{beat_id}")
                beat_ids.add(beat_id)
                actions = raw_beat.get("actions", [])
                if not isinstance(actions, list):
                    raise SceneGraphViolation("Beat actions must be a list")
                action_ids: set[str] = set()
                graph_actions: list[GraphAction] = []
                for raw_action in actions:
                    if not isinstance(raw_action, Mapping):
                        raise SceneGraphViolation("Action must be an object")
                    action_id = self._validate_identifier(raw_action.get("action_id"), "action_id")
                    if action_id in action_ids:
                        raise SceneGraphViolation(f"Duplicate action: {scene_id}/{beat_id}/{action_id}")
                    action_ids.add(action_id)
                    transition = raw_action.get("transition")
                    if not isinstance(transition, Mapping):
                        raise SceneGraphViolation("Action needs an explicit transition")
                    target = transition.get("target")
                    if not isinstance(target, Mapping):
                        raise SceneGraphViolation("Transition needs a target")
                    patch = transition.get("patch", {})
                    if not isinstance(patch, Mapping):
                        raise SceneGraphViolation("Transition patch must be an object")
                    graph_actions.append(
                        GraphAction(
                            action_id=action_id,
                            label=str(raw_action.get("label", action_id)),
                            transition_id=self._validate_identifier(transition.get("transition_id"), "transition_id"),
                            target_scene_id=self._validate_identifier(target.get("scene_id"), "target scene_id"),
                            target_beat_id=self._validate_identifier(target.get("beat_id"), "target beat_id"),
                            patch=dict(patch),
                        )
                    )
                self._beats[(scene_id, beat_id)] = GraphBeat(
                    scene_id=scene_id,
                    beat_id=beat_id,
                    text=str(raw_beat.get("text", "")),
                    recap=str(raw_beat.get("recap", raw_beat.get("text", ""))),
                    actions=tuple(graph_actions),
                )
        entry = self.manifest.get("entry")
        if not isinstance(entry, Mapping) or (entry.get("scene_id"), entry.get("beat_id")) not in self._beats:
            raise SceneGraphViolation("Manifest entry must reference an existing beat")
        transition_ids: set[str] = set()
        for beat in self._beats.values():
            for action in beat.actions:
                if action.transition_id in transition_ids:
                    raise SceneGraphViolation("Duplicate transition_id: " + action.transition_id)
                transition_ids.add(action.transition_id)
                if (action.target_scene_id, action.target_beat_id) not in self._beats:
                    raise SceneGraphViolation("Dangling transition target: " + action.transition_id)
                if action.patch.get("scene_id", action.target_scene_id) != action.target_scene_id:
                    raise SceneGraphViolation("Transition scene target disagrees with patch: " + action.transition_id)
                if action.patch.get("beat_id", action.target_beat_id) != action.target_beat_id:
                    raise SceneGraphViolation("Transition beat target disagrees with patch: " + action.transition_id)

    def initial_state(self) -> StoryState:
        entry = self.manifest["entry"]
        return StoryState(scene_id=str(entry["scene_id"]), beat_id=str(entry["beat_id"]), relationships={"mira": 0})

    def beat_for(self, state: StoryState) -> GraphBeat:
        try:
            return self._beats[(state.scene_id, state.beat_id)]
        except KeyError as error:
            raise SceneGraphViolation(f"State points to unknown beat: {state.scene_id}/{state.beat_id}") from error

    def action_for(self, state: StoryState, action_id: str) -> GraphAction:
        for action in self.beat_for(state).actions:
            if action.action_id == action_id:
                return action
        raise SceneGraphViolation(f"Action is not legal at {state.scene_id}/{state.beat_id}: {action_id}")

    def apply(self, state: StoryState, action_id: str) -> tuple[StoryState, GraphAction]:
        action = self.action_for(state, action_id)
        patch = {**action.patch, "scene_id": action.target_scene_id, "beat_id": action.target_beat_id}
        try:
            next_state = apply_state_patch(state, patch)
        except LedgerViolation as error:
            raise SceneGraphViolation(str(error)) from error
        if (next_state.scene_id, next_state.beat_id) != (action.target_scene_id, action.target_beat_id):
            raise SceneGraphViolation("Transition did not reach its declared target")
        return next_state, action


def synthetic_three_scene_manifest() -> dict[str, Any]:
    """Public-safe fixture with cross-scene branches and reconvergent outcomes."""

    return {
        "schema": "SceneManifest/v1",
        "manifest_id": "synthetic_archive_three_scene",
        "content_rating": "non_explicit",
        "adult_characters": True,
        "entry": {"scene_id": "archive_gate", "beat_id": "arrival"},
        "scenes": [
            {
                "scene_id": "archive_gate",
                "beats": [
                    {
                        "beat_id": "arrival",
                        "text": "Two adult archivists reach the rain-lit gate.",
                        "recap": "At the archive gate.",
                        "actions": [
                            {"action_id": "listen", "label": "Listen at the gate", "transition": {"transition_id": "gate_listen", "target": {"scene_id": "archive_gate", "beat_id": "echo"}, "patch": {"reveal_facts": ["a witness is inside"], "risk_delta": 1}}},
                            {"action_id": "knock", "label": "Knock and announce yourselves", "transition": {"transition_id": "gate_knock", "target": {"scene_id": "interior_archive", "beat_id": "threshold"}, "patch": {"relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}}},
                            {"action_id": "defer", "label": "Defer to daylight", "transition": {"transition_id": "gate_defer", "target": {"scene_id": "dawn_courtyard", "beat_id": "return"}, "patch": {"risk_delta": -1, "flags": {"arrival": "deferred"}}}},
                        ],
                    },
                    {
                        "beat_id": "echo",
                        "text": "A quiet voice names an old case number.",
                        "recap": "A witness has spoken from inside.",
                        "actions": [
                            {"action_id": "knock", "label": "Knock with care", "transition": {"transition_id": "echo_knock", "target": {"scene_id": "interior_archive", "beat_id": "threshold"}, "patch": {"relationship_delta": {"mira": 1}}}},
                            {"action_id": "record", "label": "Record the clue and withdraw", "transition": {"transition_id": "echo_record", "target": {"scene_id": "dawn_courtyard", "beat_id": "return"}, "patch": {"flags": {"clue": "recorded"}}}},
                        ],
                    },
                ],
            },
            {
                "scene_id": "interior_archive",
                "beats": [
                    {
                        "beat_id": "threshold",
                        "text": "The door opens a handspan; the witness asks for safety.",
                        "recap": "At the archive threshold.",
                        "actions": [
                            {"action_id": "promise", "label": "Promise to listen before acting", "transition": {"transition_id": "threshold_promise", "target": {"scene_id": "interior_archive", "beat_id": "accord"}, "patch": {"relationship_delta": {"mira": 1}, "risk_delta": -1}}},
                            {"action_id": "retreat", "label": "Offer a daylight meeting", "transition": {"transition_id": "threshold_retreat", "target": {"scene_id": "dawn_courtyard", "beat_id": "return"}, "patch": {"flags": {"meeting": "offered"}}}},
                        ],
                    },
                    {
                        "beat_id": "accord",
                        "text": "The group agrees to preserve the record until morning.",
                        "recap": "A cautious accord is reached.",
                        "actions": [
                            {"action_id": "depart", "label": "Leave together for daylight", "transition": {"transition_id": "accord_depart", "target": {"scene_id": "dawn_courtyard", "beat_id": "return"}, "patch": {"flags": {"accord": "kept"}}}}
                        ],
                    },
                ],
            },
            {
                "scene_id": "dawn_courtyard",
                "beats": [
                    {"beat_id": "return", "text": "Morning reaches the courtyard; the case remains open and traceable.", "recap": "Dawn in the courtyard.", "actions": []}
                ],
            },
        ],
    }
