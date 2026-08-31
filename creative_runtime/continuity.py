"""Canonical story-graph replay for the offline interactive-film runtime.

The ledger protects event bytes with a hash chain. This module adds semantic
protection: each player event must also be a legal edge in a versioned story
graph, and every timeline row is obtained by replaying its own ledger prefix.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Iterable, Mapping

from .contracts import StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation, apply_state_patch


_NON_EXPLICIT_CONTENT_PATTERNS = (
    re.compile(r"\b(?:sex|sexual|nude|nudity|gore|torture)\b", re.IGNORECASE),
    re.compile(r"性爱|性行为|色情|裸露|裸体|露骨|血腥|酷刑|虐待"),
)


class TimelineViolation(ValueError):
    """Raised when a valid hash chain does not represent a valid story route."""


def _hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _as_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    return dict(value)


@dataclass(frozen=True)
class GraphBeat:
    scene_id: str
    beat_id: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"scene_id": self.scene_id, "beat_id": self.beat_id, "text": self.text}


@dataclass(frozen=True)
class GraphTransition:
    transition_id: str
    scene_id: str
    from_beat_id: str
    action_id: str
    label: str
    resulting_patch: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "scene_id": self.scene_id,
            "from_beat_id": self.from_beat_id,
            "action_id": self.action_id,
            "label": self.label,
            "resulting_patch": _as_dict(self.resulting_patch),
        }


@dataclass(frozen=True)
class TimelineEntry:
    sequence: int
    event_id: str
    event_type: str
    transition_id: str | None
    action_id: str | None
    state: StoryState
    consequence: Mapping[str, Any]
    prefix_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "transition_id": self.transition_id,
            "action_id": self.action_id,
            "state": self.state.to_dict(),
            "consequence": _as_dict(self.consequence),
            "prefix_hash": self.prefix_hash,
        }


@dataclass(frozen=True)
class VerifiedDirectorInput:
    """A director-ready state retaining the verified story prefix identity."""

    state: StoryState
    graph_revision: str
    timeline_hash: str
    final_event_id: str
    final_transition_id: str | None
    final_consequence: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "graph_revision": self.graph_revision,
            "timeline_hash": self.timeline_hash,
            "final_event_id": self.final_event_id,
            "final_transition_id": self.final_transition_id,
            "final_consequence": _as_dict(self.final_consequence),
        }


class StoryGraph:
    """Versioned graph definition used to validate play and replay."""

    def __init__(self, revision: str, beats: Iterable[GraphBeat], transitions: Iterable[GraphTransition]) -> None:
        beat_items = tuple(beats)
        transition_items = tuple(transitions)
        self.revision = revision
        self._beats = {(beat.scene_id, beat.beat_id): beat for beat in beat_items}
        self._transitions = {
            (transition.scene_id, transition.from_beat_id, transition.action_id): transition
            for transition in transition_items
        }
        if not self._beats:
            raise TimelineViolation("Story graph needs at least one beat")
        if len(self._transitions) != len(transition_items):
            raise TimelineViolation("Story graph has duplicate transition keys")
        for beat in beat_items:
            self._require_non_explicit(beat.text, "story beat")
        for transition in self._transitions.values():
            self._require_non_explicit(transition.label, "transition label")
            if (transition.scene_id, transition.from_beat_id) not in self._beats:
                raise TimelineViolation("Transition has an unknown source beat: " + transition.transition_id)
            destination_scene = str(transition.resulting_patch.get("scene_id", transition.scene_id))
            destination_beat = str(transition.resulting_patch.get("beat_id", transition.from_beat_id))
            if (destination_scene, destination_beat) not in self._beats:
                raise TimelineViolation("Transition has an unknown destination beat: " + transition.transition_id)

    @staticmethod
    def _require_non_explicit(value: str, context: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise TimelineViolation(context + " must be a non-empty public-safe string")
        if any(pattern.search(value) for pattern in _NON_EXPLICIT_CONTENT_PATTERNS):
            raise TimelineViolation(context + " violates the non_explicit content boundary")

    def transition_for(self, state: StoryState, action_id: str) -> GraphTransition:
        transition = self._transitions.get((state.scene_id, state.beat_id, action_id))
        if transition is None:
            raise TimelineViolation(f"No legal transition for {state.scene_id}/{state.beat_id} action={action_id}")
        return transition

    def legal_actions(self, state: StoryState) -> tuple[GraphTransition, ...]:
        return tuple(
            transition
            for key, transition in sorted(self._transitions.items())
            if key[0] == state.scene_id and key[1] == state.beat_id
        )

    def transitions(self) -> tuple[GraphTransition, ...]:
        """Return every versioned transition in a stable order for coverage."""

        return tuple(sorted(self._transitions.values(), key=lambda item: item.transition_id))

    def beat_for(self, state: StoryState) -> GraphBeat:
        beat = self._beats.get((state.scene_id, state.beat_id))
        if beat is None:
            raise TimelineViolation(f"Unknown graph beat: {state.scene_id}/{state.beat_id}")
        return beat

    def cli_view_for(self, state: StoryState) -> dict[str, Any]:
        """Render one exact scene/beat view without collapsing duplicate beat IDs.

        ``to_cli_scene`` remains a legacy inspection convenience. Interactive
        callers must use this method because a future multi-scene graph may
        legitimately reuse a beat name such as ``arrival`` in more than one
        physical space.
        """

        beat = self.beat_for(state)
        transitions = self.legal_actions(state)
        return {
            "text": beat.text,
            "options": {
                transition.action_id: {
                    "label": transition.label,
                    "patch": _as_dict(transition.resulting_patch),
                    "transition_id": transition.transition_id,
                }
                for transition in transitions
            },
        }

    def to_cli_scene(self) -> dict[str, dict[str, Any]]:
        """Render a CLI view from the graph; there is no shadow graph."""

        result: dict[str, dict[str, Any]] = {}
        for (_, beat_id), beat in sorted(self._beats.items()):
            transitions = self.legal_actions(StoryState(scene_id=beat.scene_id, beat_id=beat.beat_id))
            result[beat_id] = {
                "text": beat.text,
                "options": {
                    transition.action_id: {
                        "label": transition.label,
                        "patch": _as_dict(transition.resulting_patch),
                        "transition_id": transition.transition_id,
                    }
                    for transition in transitions
                },
            }
        return result


def _transition(revision: str, scene_id: str, beat_id: str, action_id: str, label: str, patch: Mapping[str, Any]) -> GraphTransition:
    material = {
        "schema": "StoryGraphTransition/v1",
        "revision": revision,
        "scene_id": scene_id,
        "from_beat_id": beat_id,
        "action_id": action_id,
        "resulting_patch": _as_dict(patch),
    }
    return GraphTransition(
        transition_id="tr_" + _hash(material)[:20],
        scene_id=scene_id,
        from_beat_id=beat_id,
        action_id=action_id,
        label=label,
        resulting_patch=_as_dict(patch),
    )


def default_story_graph() -> StoryGraph:
    """Private synthetic graph retaining v1 semantics for exact legacy checks."""

    revision = "SyntheticArchiveGraph/v1"
    scene = "synthetic_archive"
    beats = (
        GraphBeat(scene, "arrival", "Two adult archivists pause outside a locked, rain-lit archive door."),
        GraphBeat(scene, "echo", "A low voice names an old case number; Mira watches the corridor."),
        GraphBeat(scene, "threshold", "The door opens a handspan. The unseen witness asks whether the archive is safe."),
        GraphBeat(scene, "courtyard", "Morning light reaches the courtyard. The case is paused, not erased."),
        GraphBeat(scene, "resolution", "The group agrees to preserve the record and meet in daylight."),
    )
    transitions = (
        _transition(revision, scene, "arrival", "listen", "Listen at the door", {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}),
        _transition(revision, scene, "arrival", "approach", "Knock and announce yourself", {"beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}),
        _transition(revision, scene, "arrival", "leave", "Step back and call for daylight", {"beat_id": "courtyard", "risk_delta": -1, "flags": {"arrival": "deferred"}}),
        _transition(revision, scene, "echo", "approach", "Ask Mira to knock", {"beat_id": "threshold", "relationship_delta": {"mira": 1}}),
        _transition(revision, scene, "echo", "leave", "Mark the clue and withdraw", {"beat_id": "courtyard", "flags": {"clue": "recorded"}}),
        _transition(revision, scene, "threshold", "listen", "Promise to listen before acting", {"beat_id": "resolution", "relationship_delta": {"mira": 1}, "risk_delta": -1}),
        _transition(revision, scene, "threshold", "leave", "Leave a safe meeting place", {"beat_id": "courtyard", "flags": {"meeting": "offered"}}),
    )
    return StoryGraph(revision, beats, transitions)


def three_scene_story_graph() -> StoryGraph:
    """A new, fully synthetic route with explicit scene transitions.

    This graph is intentionally separate from the legacy-compatible graph.
    New sessions opt into it through their initial state; old sessions therefore
    retain the exact semantics with which they were created.
    """

    revision = "ArchiveJourneyGraph/v1"
    beats = (
        GraphBeat("archive_gate", "arrival", "Two adult archivists reach the rain-dark gate of a closed municipal archive."),
        GraphBeat("archive_gate", "echo", "A witness answers through the gate while Mira checks the empty street."),
        GraphBeat("interior_archive", "threshold", "Inside the entry hall, the witness asks whether the record can remain protected."),
        GraphBeat("interior_archive", "accord", "The group aligns on a careful daylight handoff and documents what is known."),
        GraphBeat("dawn_courtyard", "return", "At dawn in the courtyard, the case is paused with a traceable next step."),
    )
    transitions = (
        _transition(revision, "archive_gate", "arrival", "listen", "Listen at the gate", {"beat_id": "echo", "reveal_facts": ["a witness is inside"], "risk_delta": 1}),
        _transition(revision, "archive_gate", "arrival", "approach", "Knock and identify the team", {"scene_id": "interior_archive", "beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}),
        _transition(revision, "archive_gate", "arrival", "leave", "Leave a daylight contact route", {"scene_id": "dawn_courtyard", "beat_id": "return", "risk_delta": -1, "flags": {"arrival": "deferred"}}),
        _transition(revision, "archive_gate", "echo", "approach", "Ask Mira to open a careful dialogue", {"scene_id": "interior_archive", "beat_id": "threshold", "relationship_delta": {"mira": 1}, "flags": {"clue": "heard"}}),
        _transition(revision, "archive_gate", "echo", "leave", "Record the lead and withdraw", {"scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"clue": "recorded"}}),
        _transition(revision, "interior_archive", "threshold", "listen", "Promise a documented handoff", {"beat_id": "accord", "relationship_delta": {"mira": 1}, "risk_delta": -1, "flags": {"handoff": "promised"}}),
        _transition(revision, "interior_archive", "threshold", "leave", "Retreat to the agreed daylight point", {"scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"meeting": "offered"}}),
        _transition(revision, "interior_archive", "accord", "leave", "Close the archive and meet at dawn", {"scene_id": "dawn_courtyard", "beat_id": "return", "flags": {"record": "preserved"}}),
    )
    return StoryGraph(revision, beats, transitions)


def night_signal_story_graph() -> StoryGraph:
    """A longer synthetic adult-only route with multiple earned exits.

    It provides a more substantial interactive-film fixture without importing
    any third-party story, character, or media material.  Every exit uses the
    same constrained action language and is therefore replayable offline.
    """

    revision = "NightSignalGraph/v1"
    beats = (
        GraphBeat("station_platform", "platform_arrival", "Two adult archivists reach an empty night platform after a protected relay starts repeating a case number."),
        GraphBeat("station_platform", "platform_signal", "The relay repeats once. Mira keeps the platform exit in view while the player decides how to document the signal."),
        GraphBeat("signal_room", "signal_console", "Inside the staffed signal room, a clerk offers a read-only relay log and waits for a careful request."),
        GraphBeat("archive_vault", "vault_crosscheck", "At the archive vault, the log and a sealed index can be compared without opening any private record."),
        GraphBeat("archive_vault", "vault_accord", "The group agrees on a daylight handoff and a minimal written record."),
        GraphBeat("control_room", "relay_console", "In the control room, the relay can be paused while its public-safe audit trail is preserved."),
        GraphBeat("control_room", "relay_accord", "The team confirms the relay is paused and schedules a witnessed daylight review."),
        GraphBeat("riverside_dawn", "dawn_return", "At dawn beside the river, the case is paused with an accountable next step and no private record exposed."),
    )
    transitions = (
        _transition(revision, "station_platform", "platform_arrival", "listen", "Listen to the relay cadence", {"beat_id": "platform_signal", "reveal_facts": ["a protected relay is active"], "risk_delta": 1}),
        _transition(revision, "station_platform", "platform_arrival", "approach", "Ask the station clerk for a safe route", {"scene_id": "signal_room", "beat_id": "signal_console", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}),
        _transition(revision, "station_platform", "platform_arrival", "leave", "Leave a daylight callback route", {"scene_id": "riverside_dawn", "beat_id": "dawn_return", "risk_delta": -1, "flags": {"route": "deferred"}}),
        _transition(revision, "station_platform", "platform_signal", "approach", "Document the relay before entering", {"scene_id": "signal_room", "beat_id": "signal_console", "relationship_delta": {"mira": 1}, "flags": {"signal": "logged"}}),
        _transition(revision, "station_platform", "platform_signal", "leave", "Record the signal and withdraw", {"scene_id": "riverside_dawn", "beat_id": "dawn_return", "flags": {"signal": "recorded"}}),
        _transition(revision, "signal_room", "signal_console", "listen", "Compare the relay log with Mira", {"scene_id": "archive_vault", "beat_id": "vault_crosscheck", "reveal_facts": ["the archive key is mirrored"], "relationship_delta": {"mira": 1}, "risk_delta": -1, "flags": {"handoff": "scoped"}}),
        _transition(revision, "signal_room", "signal_console", "leave", "Decline the log and keep the meeting public", {"scene_id": "riverside_dawn", "beat_id": "dawn_return", "flags": {"meeting": "offered"}}),
        _transition(revision, "archive_vault", "vault_crosscheck", "listen", "Read the index aloud and preserve a minimal record", {"beat_id": "vault_accord", "relationship_delta": {"mira": 1}, "flags": {"record": "verified"}}),
        _transition(revision, "archive_vault", "vault_crosscheck", "approach", "Ask control to pause the relay", {"scene_id": "control_room", "beat_id": "relay_console", "risk_delta": -1, "flags": {"relay": "escalated"}}),
        _transition(revision, "archive_vault", "vault_crosscheck", "leave", "Seal the index and return at dawn", {"scene_id": "riverside_dawn", "beat_id": "dawn_return", "flags": {"vault": "sealed"}}),
        _transition(revision, "archive_vault", "vault_accord", "leave", "Carry the witnessed handoff to dawn", {"scene_id": "riverside_dawn", "beat_id": "dawn_return", "flags": {"handoff": "scheduled"}}),
        _transition(revision, "control_room", "relay_console", "listen", "Pause the relay with a witness", {"beat_id": "relay_accord", "relationship_delta": {"mira": 1}, "flags": {"relay": "paused"}}),
        _transition(revision, "control_room", "relay_console", "leave", "Keep the relay live and return at dawn", {"scene_id": "riverside_dawn", "beat_id": "dawn_return", "flags": {"relay": "deferred"}}),
        _transition(revision, "control_room", "relay_accord", "leave", "Close the control log for daylight review", {"scene_id": "riverside_dawn", "beat_id": "dawn_return", "flags": {"review": "scheduled"}}),
    )
    return StoryGraph(revision, beats, transitions)


def harbor_protocol_story_graph() -> StoryGraph:
    """A second substantial synthetic interactive-film route.

    The route is deliberately original and public-safe: adult characters make
    documented, non-explicit choices about a civic beacon record.  Its branches
    exercise earned facts, risk, relationships, public handoff and multiple
    physical spaces without importing any external story or media asset.
    """

    revision = "HarborProtocolGraph/v1"
    beats = (
        GraphBeat("harbor_observatory", "dock_arrival", "Two adult archivists reach a quiet harbor observatory after a civic beacon repeats an old chart number."),
        GraphBeat("harbor_observatory", "beacon_echo", "The beacon answers once more. Mira keeps the pier exit visible while the player decides how to document the signal."),
        GraphBeat("beacon_room", "lens_console", "In the staffed beacon room, a keeper offers a read-only light log and waits for a careful request."),
        GraphBeat("map_archive", "chart_crosscheck", "At the map archive, a public chart index can be compared without opening a private harbor record."),
        GraphBeat("public_forum", "witnessed_record", "At the public forum, the group can state only verified facts and schedule a witnessed daylight handoff."),
        GraphBeat("sunrise_pier", "daylight_return", "At sunrise on the pier, the beacon case is paused with an accountable, public-safe next step."),
    )
    transitions = (
        _transition(revision, "harbor_observatory", "dock_arrival", "listen", "Listen to the beacon cadence", {"beat_id": "beacon_echo", "reveal_facts": ["a civic beacon is repeating a chart number"], "risk_delta": 1}),
        _transition(revision, "harbor_observatory", "dock_arrival", "approach", "Ask the harbor keeper for a safe route", {"scene_id": "beacon_room", "beat_id": "lens_console", "relationship_delta": {"mira": 1}, "flags": {"arrival": "announced"}}),
        _transition(revision, "harbor_observatory", "dock_arrival", "leave", "Leave a public daylight callback route", {"scene_id": "sunrise_pier", "beat_id": "daylight_return", "risk_delta": -1, "flags": {"route": "deferred"}}),
        _transition(revision, "harbor_observatory", "beacon_echo", "approach", "Document the signal before entering", {"scene_id": "beacon_room", "beat_id": "lens_console", "relationship_delta": {"mira": 1}, "flags": {"beacon": "logged"}}),
        _transition(revision, "harbor_observatory", "beacon_echo", "leave", "Record the beacon and withdraw", {"scene_id": "sunrise_pier", "beat_id": "daylight_return", "flags": {"beacon": "recorded"}}),
        _transition(revision, "beacon_room", "lens_console", "listen", "Compare the light log with Mira", {"scene_id": "map_archive", "beat_id": "chart_crosscheck", "reveal_facts": ["the public chart index confirms the beacon route"], "relationship_delta": {"mira": 1}, "risk_delta": -1, "flags": {"handoff": "scoped"}}),
        _transition(revision, "beacon_room", "lens_console", "leave", "Keep the discussion at the public pier", {"scene_id": "sunrise_pier", "beat_id": "daylight_return", "flags": {"meeting": "offered"}}),
        _transition(revision, "map_archive", "chart_crosscheck", "listen", "Read the public chart index into the record", {"scene_id": "public_forum", "beat_id": "witnessed_record", "relationship_delta": {"mira": 1}, "flags": {"record": "verified"}}),
        _transition(revision, "map_archive", "chart_crosscheck", "approach", "Ask for a witnessed public handoff", {"scene_id": "public_forum", "beat_id": "witnessed_record", "risk_delta": -1, "flags": {"handoff": "requested"}}),
        _transition(revision, "map_archive", "chart_crosscheck", "leave", "Seal the chart and return at sunrise", {"scene_id": "sunrise_pier", "beat_id": "daylight_return", "flags": {"chart": "sealed"}}),
        _transition(revision, "public_forum", "witnessed_record", "listen", "Confirm the witnessed record before dawn", {"scene_id": "sunrise_pier", "beat_id": "daylight_return", "relationship_delta": {"mira": 1}, "flags": {"forum": "witnessed"}}),
        _transition(revision, "public_forum", "witnessed_record", "leave", "Adjourn the public forum for daylight review", {"scene_id": "sunrise_pier", "beat_id": "daylight_return", "flags": {"forum": "adjourned"}}),
    )
    return StoryGraph(revision, beats, transitions)


def graph_for_initial_state(initial: StoryState) -> StoryGraph:
    """Select the sole graph that can interpret a session's initial state."""

    if initial.scene_id == "synthetic_archive" and initial.beat_id == "arrival":
        return default_story_graph()
    if initial.scene_id == "archive_gate" and initial.beat_id == "arrival":
        return three_scene_story_graph()
    if initial.scene_id == "station_platform" and initial.beat_id == "platform_arrival":
        return night_signal_story_graph()
    if initial.scene_id == "harbor_observatory" and initial.beat_id == "dock_arrival":
        return harbor_protocol_story_graph()
    raise TimelineViolation(
        "No registered story graph for initial state " + initial.scene_id + "/" + initial.beat_id
    )


def graph_for_ledger(ledger: CreativeLedger) -> StoryGraph:
    """Resolve a graph from immutable initialization data, never from a branch name."""

    ledger.verify_chain()
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise TimelineViolation("Timeline must start with story_initialized")
    return graph_for_initial_state(StoryState.from_dict(ledger.events[0].payload["state"]))


def _consequence(before: StoryState, after: StoryState) -> dict[str, Any]:
    relationship_delta = {
        name: after.relationships.get(name, 0) - before.relationships.get(name, 0)
        for name in sorted(set(before.relationships) | set(after.relationships))
        if after.relationships.get(name, 0) != before.relationships.get(name, 0)
    }
    return {
        "scene_changed": before.scene_id != after.scene_id,
        "beat_changed": before.beat_id != after.beat_id,
        "relationship_delta": relationship_delta,
        "new_facts": [fact for fact in after.known_facts if fact not in before.known_facts],
        "risk_delta": after.risk_level - before.risk_level,
        "flag_changes": {key: after.flags[key] for key in sorted(after.flags) if before.flags.get(key) != after.flags[key]},
    }


def _prefix_hash(records: Iterable[Mapping[str, Any]]) -> str:
    return _hash({"schema": "CreativeTimelinePrefix/v1", "events": list(records)})


def replay_timeline(ledger: CreativeLedger, graph: StoryGraph | None = None) -> tuple[TimelineEntry, ...]:
    """Replay every exact prefix and reject a hash-valid semantic forgery."""

    story_graph = graph if graph is not None else graph_for_ledger(ledger)
    ledger.verify_chain()
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise TimelineViolation("Timeline must start with story_initialized")
    initial = StoryState.from_dict(ledger.events[0].payload["state"])
    story_graph.beat_for(initial)
    entries: list[TimelineEntry] = [
        TimelineEntry(0, ledger.events[0].event_id, "story_initialized", None, None, initial, {"kind": "initialized"}, _prefix_hash([ledger.events[0].to_dict()]))
    ]
    state = initial
    for index, event in enumerate(ledger.events[1:], start=1):
        if event.event_type != "player_action":
            raise TimelineViolation("Only graph-backed player_action events are valid after initialization")
        action = event.payload.get("action")
        patch = event.payload.get("resulting_patch")
        if not isinstance(action, Mapping) or not isinstance(patch, Mapping):
            raise TimelineViolation("player_action must contain action and resulting_patch mappings")
        action_id = str(action.get("action_id", ""))
        if action.get("kind") != "choice" or not action_id:
            raise TimelineViolation("player_action must contain a non-empty choice action_id")
        transition = story_graph.transition_for(state, action_id)
        declared_transition = event.payload.get("transition_id")
        if declared_transition is not None and declared_transition != transition.transition_id:
            raise TimelineViolation("Declared transition_id does not match the graph edge")
        declared_revision = event.payload.get("graph_revision")
        if declared_revision is not None and declared_revision != story_graph.revision:
            raise TimelineViolation("Declared graph_revision does not match the replay graph")
        if canonical_json(patch) != canonical_json(transition.resulting_patch):
            raise TimelineViolation("resulting_patch is not semantically equal to the graph transition")
        try:
            next_state = apply_state_patch(state, transition.resulting_patch)
        except LedgerViolation as error:
            raise TimelineViolation("Graph transition has an invalid state patch") from error
        story_graph.beat_for(next_state)
        replayed_prefix_state = CreativeLedger(ledger.events[: index + 1]).replay()
        if replayed_prefix_state != next_state:
            raise TimelineViolation("Ledger replay diverges from graph-backed prefix replay")
        entries.append(
            TimelineEntry(
                index,
                event.event_id,
                event.event_type,
                transition.transition_id,
                action_id,
                next_state,
                _consequence(state, next_state),
                _prefix_hash(item.to_dict() for item in ledger.events[: index + 1]),
            )
        )
        state = next_state
    return tuple(entries)


def timeline_hash(entries: Iterable[TimelineEntry]) -> str:
    return _hash({"schema": "CreativeTimeline/v1", "entries": [entry.to_dict() for entry in entries]})


def verified_director_input(ledger: CreativeLedger, graph: StoryGraph | None = None) -> VerifiedDirectorInput:
    """Return a director input only after every prefix has passed graph replay."""

    story_graph = graph if graph is not None else graph_for_ledger(ledger)
    entries = replay_timeline(ledger, story_graph)
    final = entries[-1]
    return VerifiedDirectorInput(
        final.state,
        story_graph.revision,
        timeline_hash(entries),
        final.event_id,
        final.transition_id,
        final.consequence,
    )
