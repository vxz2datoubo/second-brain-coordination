"""Fixed v2 scene transitions; callers may select actions but never patches."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from .contracts import StoryState
from .ledger import LedgerViolation, apply_state_patch

@dataclass(frozen=True)
class GraphMove:
    action: str
    transition: str
    patch: Mapping[str, Any]

_MOVES = {
    ("archive_gate", "arrival"): {
        "listen": GraphMove("listen", "gate_listen", {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}),
        "knock": GraphMove("knock", "gate_knock", {"scene_id": "interior_archive", "beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}),
        "defer": GraphMove("defer", "gate_defer", {"scene_id": "dawn_courtyard", "beat_id": "return", "risk_delta": -1, "flags": {"arrival": "deferred"}}),
    },
    ("archive_gate", "echo"): {
        "knock": GraphMove("knock", "echo_knock", {"scene_id": "interior_archive", "beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"clue": "heard"}}),
        "record": GraphMove("record", "echo_record", {"scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"clue": "recorded"}}),
    },
    ("interior_archive", "threshold"): {
        "promise": GraphMove("promise", "threshold_promise", {"beat_id": "accord", "relationship_delta": {"mira": 1}, "risk_delta": -1}),
        "retreat": GraphMove("retreat", "threshold_retreat", {"scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"meeting": "offered"}}),
    },
}

def initial() -> StoryState:
    return StoryState("archive_gate", "arrival", relationships={"mira": 0})

def move(state: StoryState, action: str) -> tuple[GraphMove, StoryState]:
    item = _MOVES.get((state.scene_id, state.beat_id), {}).get(action)
    if item is None:
        raise LedgerViolation("Action is not legal in the current v2 state")
    return item, apply_state_patch(state, item.patch)
