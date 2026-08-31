"""The current, deterministic interactive-film scene graph.

The graph is the only authority that can turn a player action into a state
change.  Persisted patches are receipts which must be compared to this graph;
they are never instructions supplied by a caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import StoryState
from .ledger import LedgerViolation, apply_state_patch


@dataclass(frozen=True)
class Transition:
    transition_id: str
    action_id: str
    patch: Mapping[str, Any]


def initial_story_state() -> StoryState:
    return StoryState("archive_gate", "arrival", relationships={"mira": 0})


class SceneGraph:
    """A small graph deliberately kept inspectable for offline replay."""

    _TRANSITIONS: dict[tuple[str, str], dict[str, Transition]] = {
        ("archive_gate", "arrival"): {
            "listen": Transition("gate_listen", "listen", {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}),
            "knock": Transition("gate_knock", "knock", {"scene_id": "interior_archive", "beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}),
            "defer": Transition("gate_defer", "defer", {"scene_id": "dawn_courtyard", "beat_id": "return", "risk_delta": -1, "flags": {"arrival": "deferred"}}),
        },
        ("archive_gate", "echo"): {
            "knock": Transition("echo_knock", "knock", {"scene_id": "interior_archive", "beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"clue": "heard"}}),
            "record": Transition("echo_record", "record", {"scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"clue": "recorded"}}),
        },
        ("interior_archive", "threshold"): {
            "promise": Transition("threshold_promise", "promise", {"beat_id": "accord", "relationship_delta": {"mira": 1}, "risk_delta": -1}),
            "retreat": Transition("threshold_retreat", "retreat", {"scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"meeting": "offered"}}),
        },
    }

    def legal_actions(self, state: StoryState) -> tuple[str, ...]:
        return tuple(self._TRANSITIONS.get((state.scene_id, state.beat_id), {}))

    def transition(self, state: StoryState, action_id: str) -> tuple[Transition, StoryState]:
        transition = self._TRANSITIONS.get((state.scene_id, state.beat_id), {}).get(action_id)
        if transition is None:
            raise LedgerViolation("Unknown or illegal graph action: " + action_id)
        return transition, apply_state_patch(state, transition.patch)

    def validate_action_record(self, state: StoryState, payload: Mapping[str, Any]) -> StoryState:
        action = payload.get("action")
        if not isinstance(action, Mapping):
            raise LedgerViolation("player_action requires an action mapping")
        action_id = str(action.get("action_id", ""))
        transition, next_state = self.transition(state, action_id)
        if payload.get("transition_id") != transition.transition_id:
            raise LedgerViolation("player_action transition_id does not match SceneGraph")
        patch = payload.get("resulting_patch")
        if not isinstance(patch, Mapping) or dict(patch) != dict(transition.patch):
            raise LedgerViolation("player_action resulting_patch does not match SceneGraph")
        return next_state
