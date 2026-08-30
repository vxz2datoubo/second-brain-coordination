"""Truthful per-event replay for an already validated saved session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import StoryState
from .saves import SavedSession, SaveViolation
from .scene_graph import SceneGraph, initial_story_state


class TimelineViolation(SaveViolation):
    pass


@dataclass(frozen=True)
class TimelineFrame:
    index: int
    state: StoryState
    action_id: str | None
    transition_id: str | None
    consequence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.index, "state": self.state.to_dict(), "action_id": self.action_id, "transition_id": self.transition_id, "consequence": self.consequence}


def timeline(session: SavedSession) -> tuple[TimelineFrame, ...]:
    """Validate the full envelope before rendering any immutable prefix."""
    try:
        session.validate()
    except SaveViolation as error:
        raise TimelineViolation(str(error)) from error
    graph = SceneGraph()
    state = initial_story_state()
    frames = [TimelineFrame(0, state, None, None, {"kind": "init"})]
    for index, event in enumerate(session.ledger.events[1:], start=1):
        if event.event_type == "migration_bridge":
            frames.append(TimelineFrame(index, state, None, "legacy_terminal_bridge", {"kind": "migration_bridge"}))
            continue
        action = event.payload["action"]
        transition, state = graph.transition(state, str(action["action_id"]))
        frames.append(TimelineFrame(index, state, str(action["action_id"]), transition.transition_id, dict(transition.patch)))
    return tuple(frames)
