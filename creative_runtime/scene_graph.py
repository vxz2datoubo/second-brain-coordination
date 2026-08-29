"""The small, explicit v2 scene graph used by the offline film prototype.

This module is intentionally deterministic.  It is the authority for normal
player transitions; append-only event hashes in the ledger are integrity
checks, not permission to invent another transition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import StoryState
from .ledger import LedgerViolation, apply_state_patch


@dataclass(frozen=True)
class Transition:
    transition_id: str
    scene_id: str
    beat_id: str
    action_id: str
    patch: Mapping[str, Any]
    label: str


class SceneGraphViolation(LedgerViolation):
    """An event does not correspond to the declared v2 graph."""


class SceneGraph:
    def __init__(self) -> None:
        self.initial_state = StoryState(
            scene_id="archive_gate", beat_id="arrival", relationships={"mira": 0}
        )
        transitions = (
            Transition("gate_listen", "archive_gate", "arrival", "listen", {
                "scene_id": "archive_gate", "beat_id": "echo",
                "reveal_facts": ["a witness is inside"], "risk_delta": 1,
            }, "Listen at the gate"),
            Transition("gate_knock", "archive_gate", "arrival", "knock", {
                "scene_id": "interior_archive", "beat_id": "threshold",
                "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"},
            }, "Knock and announce yourself"),
            Transition("gate_defer", "archive_gate", "arrival", "defer", {
                "scene_id": "dawn_courtyard", "beat_id": "return",
                "risk_delta": -1, "flags": {"arrival": "deferred"},
            }, "Step back for daylight"),
            Transition("echo_knock", "archive_gate", "echo", "knock", {
                "scene_id": "interior_archive", "beat_id": "threshold",
                "relationship_delta": {"mira": 1}, "flags": {"clue": "heard"},
            }, "Ask Mira to knock"),
            Transition("echo_record", "archive_gate", "echo", "record", {
                "scene_id": "dawn_courtyard", "beat_id": "return",
                "flags": {"clue": "recorded"},
            }, "Record the clue and withdraw"),
            Transition("threshold_promise", "interior_archive", "threshold", "promise", {
                "scene_id": "interior_archive", "beat_id": "accord",
                "relationship_delta": {"mira": 1}, "risk_delta": -1,
            }, "Promise to listen before acting"),
            Transition("threshold_retreat", "interior_archive", "threshold", "retreat", {
                "scene_id": "dawn_courtyard", "beat_id": "return",
                "flags": {"meeting": "offered"},
            }, "Leave a safe meeting place"),
        )
        self._by_key = {(item.scene_id, item.beat_id, item.action_id): item for item in transitions}
        self._by_id = {item.transition_id: item for item in transitions}

    def legal_actions(self, state: StoryState) -> tuple[str, ...]:
        return tuple(sorted(key[2] for key in self._by_key if key[:2] == (state.scene_id, state.beat_id)))

    def transition_for(self, state: StoryState, action_id: str) -> Transition:
        try:
            return self._by_key[(state.scene_id, state.beat_id, action_id)]
        except KeyError as error:
            raise SceneGraphViolation("Illegal action for current scene graph state") from error

    def apply(self, state: StoryState, action_id: str) -> tuple[Transition, StoryState]:
        transition = self.transition_for(state, action_id)
        return transition, apply_state_patch(state, transition.patch)

    def verify_event(self, state: StoryState, payload: Mapping[str, Any]) -> StoryState:
        action = payload.get("action")
        if not isinstance(action, Mapping):
            raise SceneGraphViolation("player_action requires a structured action")
        action_id = str(action.get("action_id", ""))
        transition, expected = self.apply(state, action_id)
        if payload.get("transition_id") != transition.transition_id:
            raise SceneGraphViolation("player_action transition_id does not match the scene graph")
        patch = payload.get("resulting_patch")
        if not isinstance(patch, Mapping) or dict(patch) != dict(transition.patch):
            raise SceneGraphViolation("player_action resulting_patch does not match the scene graph")
        return expected


DEFAULT_SCENE_GRAPH = SceneGraph()
