"""Deterministic branch coverage for the bounded offline story graphs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from .continuity import StoryGraph, TimelineViolation, default_story_graph, night_signal_story_graph, three_scene_story_graph
from .contracts import PlayerAction, StoryState, canonical_json
from .director import compile_verified_director
from .ledger import CreativeLedger, apply_state_patch


class RouteCoverageViolation(ValueError):
    """Raised when a graph cannot be exhaustively covered within its fixed bound."""


@dataclass(frozen=True)
class RouteCoverageEntry:
    route_id: str
    action_ids: tuple[str, ...]
    transition_ids: tuple[str, ...]
    final_state: StoryState
    timeline_hash: str
    director_can_generate: bool
    director_metrics: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "action_ids": list(self.action_ids),
            "transition_ids": list(self.transition_ids),
            "final_state": self.final_state.to_dict(),
            "timeline_hash": self.timeline_hash,
            "director_can_generate": self.director_can_generate,
            "director_metrics": dict(self.director_metrics),
        }


@dataclass(frozen=True)
class RouteCoverageReport:
    graph_revision: str
    initial_state: StoryState
    routes: tuple[RouteCoverageEntry, ...]
    covered_transition_ids: tuple[str, ...]
    expected_transition_ids: tuple[str, ...]
    terminal_state_counts: Mapping[str, int]
    report_hash: str

    @property
    def complete(self) -> bool:
        return self.covered_transition_ids == self.expected_transition_ids and all(route.director_can_generate for route in self.routes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "CreativeRouteCoverageReport/v1",
            "status": "route_coverage_verified" if self.complete else "route_coverage_incomplete",
            "graph_revision": self.graph_revision,
            "initial_state": self.initial_state.to_dict(),
            "route_count": len(self.routes),
            "covered_transition_ids": list(self.covered_transition_ids),
            "expected_transition_ids": list(self.expected_transition_ids),
            "terminal_state_counts": dict(self.terminal_state_counts),
            "routes": [route.to_dict() for route in self.routes],
            "report_hash": self.report_hash,
        }


def _terminal_paths(
    graph: StoryGraph,
    state: StoryState,
    *,
    actions: tuple[str, ...] = (),
    transitions: tuple[str, ...] = (),
    max_steps: int,
) -> tuple[tuple[tuple[str, ...], tuple[str, ...], StoryState], ...]:
    legal = graph.legal_actions(state)
    if not legal:
        return ((actions, transitions, state),)
    if len(actions) >= max_steps:
        raise RouteCoverageViolation("Story graph exceeds the fixed exhaustive route depth")
    routes: list[tuple[tuple[str, ...], tuple[str, ...], StoryState]] = []
    for transition in legal:
        next_state = apply_state_patch(state, transition.resulting_patch)
        routes.extend(
            _terminal_paths(
                graph,
                next_state,
                actions=actions + (transition.action_id,),
                transitions=transitions + (transition.transition_id,),
                max_steps=max_steps,
            )
        )
    return tuple(routes)


def ledger_for_route(graph: StoryGraph, initial_state: StoryState, actions: Iterable[str]) -> CreativeLedger:
    """Reconstruct one graph route with the exact production event contract.

    Route catalogues and exhaustive coverage share this helper so no browser
    demo or test-only serializer can create a shadow action format.
    """
    ledger = CreativeLedger()
    ledger.append("story_initialized", {"state": initial_state.to_dict()}, "2030-01-01T00:00:00Z")
    state = initial_state
    for action_id in actions:
        transition = graph.transition_for(state, action_id)
        ledger.append(
            "player_action",
            {
                # Coverage must exercise the same accepted player-action
                # contract as the CLI; it may not introduce a test-only kind.
                "action": PlayerAction(action_id, "choice", transition.label).to_dict(),
                "resulting_patch": dict(transition.resulting_patch),
                "transition_id": transition.transition_id,
                "graph_revision": graph.revision,
            },
            f"2030-01-01T00:{len(ledger.events):02d}:00Z",
        )
        state = apply_state_patch(state, transition.resulting_patch)
    return ledger


def cover_routes(graph: StoryGraph, initial_state: StoryState, *, max_steps: int = 12) -> RouteCoverageReport:
    """Exhaustively verify every terminal route in an explicitly bounded graph."""

    if max_steps < 1:
        raise RouteCoverageViolation("Route coverage max_steps must be positive")
    try:
        graph.beat_for(initial_state)
        paths = _terminal_paths(graph, initial_state, max_steps=max_steps)
    except TimelineViolation as error:
        raise RouteCoverageViolation("Route coverage graph is invalid") from error
    entries: list[RouteCoverageEntry] = []
    terminal_counts: dict[str, int] = {}
    for actions, transition_ids, expected_state in paths:
        ledger = ledger_for_route(graph, initial_state, actions)
        compiled = compile_verified_director(ledger, graph=graph)
        if compiled.verified_input.state != expected_state:
            raise RouteCoverageViolation("Route replay diverges from graph traversal")
        route_material = {
            "schema": "CreativeRouteCoverageEntry/v1",
            "graph_revision": graph.revision,
            "initial_state": initial_state.to_dict(),
            "action_ids": list(actions),
            "transition_ids": list(transition_ids),
            "timeline_hash": compiled.verified_input.timeline_hash,
        }
        route_id = "route_" + hashlib.sha256(canonical_json(route_material).encode("utf-8")).hexdigest()[:20]
        terminal_key = expected_state.scene_id + "/" + expected_state.beat_id
        terminal_counts[terminal_key] = terminal_counts.get(terminal_key, 0) + 1
        entries.append(
            RouteCoverageEntry(
                route_id=route_id,
                action_ids=actions,
                transition_ids=transition_ids,
                final_state=expected_state,
                timeline_hash=compiled.verified_input.timeline_hash,
                director_can_generate=compiled.compilation.quality_report.can_generate,
                director_metrics=compiled.compilation.quality_report.metrics.to_dict(),
            )
        )
    ordered_entries = tuple(sorted(entries, key=lambda item: item.route_id))
    covered = tuple(sorted({transition_id for route in ordered_entries for transition_id in route.transition_ids}))
    expected = tuple(sorted(transition.transition_id for transition in graph.transitions()))
    material = {
        "schema": "CreativeRouteCoverageReport/v1",
        "graph_revision": graph.revision,
        "initial_state": initial_state.to_dict(),
        "routes": [entry.to_dict() for entry in ordered_entries],
        "covered_transition_ids": list(covered),
        "expected_transition_ids": list(expected),
        "terminal_state_counts": {key: terminal_counts[key] for key in sorted(terminal_counts)},
    }
    return RouteCoverageReport(
        graph_revision=graph.revision,
        initial_state=initial_state,
        routes=ordered_entries,
        covered_transition_ids=covered,
        expected_transition_ids=expected,
        terminal_state_counts={key: terminal_counts[key] for key in sorted(terminal_counts)},
        report_hash=hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest(),
    )


def coverage_for_scenario(scenario: str) -> RouteCoverageReport:
    """Expose only the two bounded, synthetic scenarios accepted by the CLI."""

    if scenario == "legacy_archive":
        return cover_routes(default_story_graph(), StoryState("synthetic_archive", "arrival", {"mira": 0}))
    if scenario == "three_scene":
        return cover_routes(three_scene_story_graph(), StoryState("archive_gate", "arrival", {"mira": 0}))
    if scenario == "night_signal":
        return cover_routes(night_signal_story_graph(), StoryState("station_platform", "platform_arrival", {"mira": 0}))
    raise RouteCoverageViolation("Unknown coverage scenario: " + scenario)
