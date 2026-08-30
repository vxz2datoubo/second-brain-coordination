"""Portable, verified interactive-film experience manifests.

This module deliberately produces a static projection from an append-only
ledger.  A browser, desktop shell, or later local customer adapter may render
the result, but cannot use it to invent a transition, disclose a hidden fact,
or bypass the director quality gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .continuity import TimelineViolation, graph_for_initial_state, graph_for_ledger, replay_timeline, timeline_hash
from .contracts import canonical_json
from .coverage import coverage_for_scenario, ledger_for_route
from .ledger import CreativeLedger
from .presentation import PresentationViolation, build_interactive_frame
from .session import DEFAULT_SLOT, validate_slot


class ExperienceViolation(ValueError):
    """Raised when a portable experience cannot be reproduced exactly."""


@dataclass(frozen=True)
class VerifiedExperienceManifest:
    """A render-only sequence of verified frames for one immutable ledger."""

    experience_id: str
    slot_id: str
    graph_revision: str
    timeline_hash: str
    source_event_ids: tuple[str, ...]
    frames: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "VerifiedInteractiveExperience/v1",
            "status": "experience_manifest_verified",
            "experience_id": self.experience_id,
            "slot_id": self.slot_id,
            "graph_revision": self.graph_revision,
            "timeline_hash": self.timeline_hash,
            "source_event_ids": list(self.source_event_ids),
            "frames": [dict(frame) for frame in self.frames],
            "provenance": {
                "class": "private_adaptation",
                "synthetic_only": True,
                "public_release_authorized": False,
                "customer_data_present": False,
                "external_provider_called": False,
            },
        }


def build_verified_experience(ledger: CreativeLedger, *, slot: str = DEFAULT_SLOT) -> VerifiedExperienceManifest:
    """Build one deterministic frame per verified ledger prefix.

    Each prefix is reconstructed as an independent ``CreativeLedger``.  This
    is intentionally more expensive than mutating a single display state: it
    prevents a final-state field from being silently backfilled into an earlier
    frame.
    """

    normalized_slot = validate_slot(slot)
    try:
        graph = graph_for_ledger(ledger)
        timeline = replay_timeline(ledger, graph)
        frames = tuple(
            build_interactive_frame(CreativeLedger(ledger.events[: index + 1]), slot=normalized_slot).to_dict()
            for index in range(len(timeline))
        )
    except (PresentationViolation, TimelineViolation, TypeError, ValueError) as error:
        raise ExperienceViolation("Verified experience requires a complete verified story timeline") from error
    if not frames:
        raise ExperienceViolation("Verified experience requires at least one frame")
    if frames[-1]["timeline_hash"] != timeline_hash(timeline):
        raise ExperienceViolation("Final experience frame is not bound to the full timeline")
    if len({str(frame["frame_id"]) for frame in frames}) != len(frames):
        raise ExperienceViolation("Experience contains duplicate verified frame identities")
    source_event_ids = tuple(event.event_id for event in ledger.events)
    material = {
        "schema": "VerifiedInteractiveExperience/v1",
        "slot_id": normalized_slot,
        "graph_revision": graph.revision,
        "timeline_hash": timeline_hash(timeline),
        "source_event_ids": list(source_event_ids),
        "frames": list(frames),
    }
    experience_id = "experience_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20]
    return VerifiedExperienceManifest(
        experience_id=experience_id,
        slot_id=normalized_slot,
        graph_revision=graph.revision,
        timeline_hash=timeline_hash(timeline),
        source_event_ids=source_event_ids,
        frames=frames,
    )


def verify_verified_experience(ledger: CreativeLedger, manifest: Mapping[str, Any], *, slot: str = DEFAULT_SLOT) -> VerifiedExperienceManifest:
    """Reject any byte-level or semantic change to a claimed experience."""

    expected = build_verified_experience(ledger, slot=slot)
    try:
        supplied = dict(manifest)
    except (TypeError, ValueError) as error:
        raise ExperienceViolation("Experience manifest must be a JSON object") from error
    if canonical_json(supplied) != canonical_json(expected.to_dict()):
        raise ExperienceViolation("Experience manifest does not exactly match the verified ledger")
    return expected


@dataclass(frozen=True)
class VerifiedScenarioCatalog:
    """A complete, render-only graph projection for one bounded scenario.

    Nodes are verified presentation frames. Edges merely point to another
    already-built frame; the client receives no state-patch language and cannot
    calculate alternate story states itself.
    """

    catalog_id: str
    scenario: str
    graph_revision: str
    coverage_report_hash: str
    initial_timeline_hash: str
    nodes: tuple[Mapping[str, Any], ...]
    edges: tuple[Mapping[str, str], ...]
    covered_transition_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "VerifiedInteractiveScenarioCatalog/v1",
            "status": "scenario_catalog_verified",
            "catalog_id": self.catalog_id,
            "scenario": self.scenario,
            "graph_revision": self.graph_revision,
            "coverage_report_hash": self.coverage_report_hash,
            "initial_timeline_hash": self.initial_timeline_hash,
            "nodes": [dict(node) for node in self.nodes],
            "edges": [dict(edge) for edge in self.edges],
            "covered_transition_ids": list(self.covered_transition_ids),
            "provenance": {
                "class": "private_adaptation",
                "synthetic_only": True,
                "public_release_authorized": False,
                "customer_data_present": False,
                "external_provider_called": False,
                "client_story_authority": False,
            },
        }


def build_verified_scenario_catalog(scenario: str) -> VerifiedScenarioCatalog:
    """Compile every bounded terminal path into a client-safe navigation map."""

    report = coverage_for_scenario(scenario)
    if not report.complete:
        raise ExperienceViolation("Scenario coverage must be complete before a client catalogue is built")
    graph = graph_for_initial_state(report.initial_state)
    nodes: dict[str, Mapping[str, Any]] = {}
    edges: dict[tuple[str, str], Mapping[str, str]] = {}
    initial_timeline_hash: str | None = None
    for route in report.routes:
        ledger = ledger_for_route(graph, report.initial_state, route.action_ids)
        manifest = build_verified_experience(ledger, slot="catalog")
        frames = tuple(manifest.frames)
        if initial_timeline_hash is None:
            initial_timeline_hash = manifest.timeline_hash if len(frames) == 1 else str(frames[0]["timeline_hash"])
        for frame in frames:
            frame_hash = str(frame["timeline_hash"])
            existing = nodes.get(frame_hash)
            if existing is not None and canonical_json(existing) != canonical_json(frame):
                raise ExperienceViolation("A timeline prefix produced conflicting client frames")
            nodes[frame_hash] = frame
        for index in range(1, len(frames)):
            previous_hash = str(frames[index - 1]["timeline_hash"])
            current_hash = str(frames[index]["timeline_hash"])
            action_id = frames[index]["recent_action"].get("action_id")
            transition_id = frames[index]["recent_action"].get("transition_id")
            if not isinstance(action_id, str) or not action_id or not isinstance(transition_id, str) or not transition_id:
                raise ExperienceViolation("Scenario catalogue edge lacks verified action provenance")
            edge = {
                "from_timeline_hash": previous_hash,
                "action_id": action_id,
                "transition_id": transition_id,
                "to_timeline_hash": current_hash,
            }
            key = (previous_hash, action_id)
            existing = edges.get(key)
            if existing is not None and canonical_json(existing) != canonical_json(edge):
                raise ExperienceViolation("Scenario catalogue contains a conflicting action edge")
            edges[key] = edge
    if initial_timeline_hash is None or initial_timeline_hash not in nodes:
        raise ExperienceViolation("Scenario catalogue has no verified initial frame")
    ordered_nodes = tuple(
        {"timeline_hash": key, "frame": dict(nodes[key])}
        for key in sorted(nodes)
    )
    ordered_edges = tuple(edges[key] for key in sorted(edges))
    covered_transition_ids = tuple(sorted({str(edge["transition_id"]) for edge in ordered_edges}))
    if covered_transition_ids != report.covered_transition_ids:
        raise ExperienceViolation("Scenario catalogue does not cover the verified transition set")
    material = {
        "schema": "VerifiedInteractiveScenarioCatalog/v1",
        "scenario": scenario,
        "graph_revision": report.graph_revision,
        "coverage_report_hash": report.report_hash,
        "initial_timeline_hash": initial_timeline_hash,
        "nodes": list(ordered_nodes),
        "edges": list(ordered_edges),
        "covered_transition_ids": list(covered_transition_ids),
    }
    catalog_id = "catalog_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20]
    return VerifiedScenarioCatalog(
        catalog_id=catalog_id,
        scenario=scenario,
        graph_revision=report.graph_revision,
        coverage_report_hash=report.report_hash,
        initial_timeline_hash=initial_timeline_hash,
        nodes=ordered_nodes,
        edges=ordered_edges,
        covered_transition_ids=covered_transition_ids,
    )


def verify_verified_scenario_catalog(scenario: str, catalog: Mapping[str, Any]) -> VerifiedScenarioCatalog:
    """Reject a tampered or stale static client catalogue."""

    expected = build_verified_scenario_catalog(scenario)
    try:
        supplied = dict(catalog)
    except (TypeError, ValueError) as error:
        raise ExperienceViolation("Scenario catalogue must be a JSON object") from error
    if canonical_json(supplied) != canonical_json(expected.to_dict()):
        raise ExperienceViolation("Scenario catalogue does not exactly match exhaustive verified coverage")
    return expected
