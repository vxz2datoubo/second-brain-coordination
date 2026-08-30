"""The small, deterministic v2 scene graph used by saved sessions.

This module is deliberately data-first.  A caller cannot choose a patch: it
must choose an action which the current node owns, and this graph supplies the
only resulting transition and patch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import StoryState
from .ledger import LedgerViolation, apply_state_patch


@dataclass(frozen=True)
class Transition:
    action_id: str
    transition_id: str
    patch: Mapping[str, Any]


_GRAPH: dict[tuple[str, str], dict[str, Transition]] = {
    ("archive_gate", "arrival"): {
        "listen": Transition("listen", "gate_listen", {
            "beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1,
        }),
        "knock": Transition("knock", "gate_knock", {
            "scene_id": "interior_archive", "beat_id": "threshold",
            "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"},
        }),
        "defer": Transition("defer", "gate_defer", {
            "scene_id": "dawn_courtyard", "beat_id": "return", "risk_delta": -1,
            "flags": {"arrival": "deferred"},
        }),
    },
    ("archive_gate", "echo"): {
        "knock": Transition("knock", "echo_knock", {
            "scene_id": "interior_archive", "beat_id": "threshold",
            "relationship_delta": {"mira": 1}, "flags": {"clue": "heard"},
        }),
        "record": Transition("record", "echo_record", {
            "scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"clue": "recorded"},
        }),
    },
    ("interior_archive", "threshold"): {
        "promise": Transition("promise", "threshold_promise", {
            "beat_id": "accord", "relationship_delta": {"mira": 1}, "risk_delta": -1,
        }),
        "retreat": Transition("retreat", "threshold_retreat", {
            "scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"meeting": "offered"},
        }),
    },
}


def initial_state() -> StoryState:
    return StoryState("archive_gate", "arrival", relationships={"mira": 0})


def transition_for(state: StoryState, action_id: str) -> Transition:
    transition = _GRAPH.get((state.scene_id, state.beat_id), {}).get(action_id)
    if transition is None:
        raise LedgerViolation("Illegal action for current scene: " + action_id)
    return transition


def apply_transition(state: StoryState, action_id: str) -> tuple[Transition, StoryState]:
    transition = transition_for(state, action_id)
    return transition, apply_state_patch(state, transition.patch)


def legal_actions(state: StoryState) -> tuple[str, ...]:
    return tuple(sorted(_GRAPH.get((state.scene_id, state.beat_id), {})))
