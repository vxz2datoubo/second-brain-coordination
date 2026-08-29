"""Deterministic per-event prefix timeline for the offline creative runtime.

The timeline is derived from the hash-chained ledger and the validated scene graph.
It never invents intermediate state: every entry is the replay result of the exact
ledger prefix ending at that event. Player-action entries are additionally checked
against the scene graph transition contract and fail closed on disagreement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation
from .scene_graph import SceneGraph, SceneGraphViolation


class TimelineViolation(ValueError):
    """Raised when the ledger cannot truthfully produce a graph-consistent timeline."""


@dataclass(frozen=True)
class TimelineEntry:
    turn: int
    event_id: str
    event_type: str
    action_id: str | None
    transition_id: str | None
    state: StoryState

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "action_id": self.action_id,
            "transition_id": self.transition_id,
            "state": self.state.to_dict(),
        }


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TimelineViolation(f"{label} must be an object")
    return value


def _expected_player_action(
    graph: SceneGraph,
    state_before: StoryState,
    event_payload: Mapping[str, Any],
) -> tuple[str, str, StoryState]:
    action = _require_mapping(event_payload.get("action"), "player_action.action")
    action_id = str(action.get("action_id", ""))
    if not action_id:
        raise TimelineViolation("player_action is missing action_id")
    try:
        expected_state, graph_action = graph.apply(state_before, action_id)
    except SceneGraphViolation as error:
        raise TimelineViolation(
            f"ledger action is not legal at {state_before.scene_id}/{state_before.beat_id}: {action_id}"
        ) from error

    transition_id = str(event_payload.get("transition_id", ""))
    if transition_id != graph_action.transition_id:
        raise TimelineViolation(
            f"transition_id disagrees with scene graph for {action_id}: "
            f"observed={transition_id!r} expected={graph_action.transition_id!r}"
        )

    observed_patch = _require_mapping(event_payload.get("resulting_patch"), "player_action.resulting_patch")
    expected_patch = {
        **dict(graph_action.patch),
        "scene_id": expected_state.scene_id,
        "beat_id": expected_state.beat_id,
    }
    if canonical_json(dict(observed_patch)) != canonical_json(expected_patch):
        raise TimelineViolation(
            f"resulting_patch disagrees with scene graph for transition {transition_id}"
        )
    return action_id, transition_id, expected_state


def build_prefix_timeline(ledger: CreativeLedger, graph: SceneGraph) -> tuple[TimelineEntry, ...]:
    """Return exact post-event states for every ledger prefix.

    Each entry is computed by rebuilding and replaying the exact prefix rather than
    reusing the final state. This deliberately favors mechanical truth over speed.
    Any malformed hash chain, unsupported event semantics, graph-invalid state, or
    player-action/graph disagreement aborts the whole timeline instead of emitting
    a partially false history.
    """

    records = ledger.to_records()
    if not records:
        raise TimelineViolation("timeline requires a non-empty ledger")

    entries: list[TimelineEntry] = []
    state_before: StoryState | None = None
    for index, event in enumerate(ledger.events):
        try:
            prefix = CreativeLedger.from_records(records[: index + 1])
            state_after = prefix.replay()
            graph.beat_for(state_after)
        except (KeyError, LedgerViolation, SceneGraphViolation, TypeError, ValueError) as error:
            raise TimelineViolation(f"event prefix {index} is not replayable and graph-valid") from error

        action_id: str | None = None
        transition_id: str | None = None
        if event.event_type == "story_initialized":
            if index != 0:
                raise TimelineViolation("story_initialized may only be the first event")
            if state_after != graph.initial_state():
                raise TimelineViolation("story_initialized state disagrees with scene graph initial state")
        elif event.event_type == "player_action":
            if state_before is None:
                raise TimelineViolation("player_action has no prior state")
            action_id, transition_id, expected_state = _expected_player_action(graph, state_before, event.payload)
            if state_after != expected_state:
                raise TimelineViolation(
                    f"prefix replay state disagrees with graph transition {transition_id}"
                )
        elif event.event_type == "state_patch":
            # State patches are retained for explicit migration/maintenance events.
            # They are accepted only when the resulting state is still a valid graph beat;
            # graph.beat_for(state_after) above is the fail-closed boundary.
            _require_mapping(event.payload.get("patch"), "state_patch.patch")
        else:
            raise TimelineViolation(f"unsupported timeline event type: {event.event_type}")

        entries.append(
            TimelineEntry(
                turn=event.sequence,
                event_id=event.event_id,
                event_type=event.event_type,
                action_id=action_id,
                transition_id=transition_id,
                state=state_after,
            )
        )
        state_before = state_after

    if [entry.turn for entry in entries] != list(range(len(entries))):
        raise TimelineViolation("ledger sequence is not contiguous")
    return tuple(entries)
