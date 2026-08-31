"""Portable, deterministic replay capsules for synthetic interactive-film runs.

The static scenario library proves every *possible* route.  A replay capsule
proves one *actually played* route without asking a viewer to trust the local
workspace that produced it.  It is intentionally constrained to the built-in
synthetic scenarios: a route containing caller-provided free text, unknown
events, a non-canonical action label, or an unregistered initial state cannot
be exported.  That keeps this Git-tracked artifact separate from a future,
approved customer-data export path.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .continuity import StoryGraph, TimelineViolation, graph_for_ledger, replay_timeline, timeline_hash
from .contracts import PlayerAction, StoryState, canonical_json
from .coverage import coverage_for_scenario
from .director import compile_verified_director
from .experience import build_verified_experience, build_verified_scenario_catalog
from .ledger import CreativeLedger, LedgerViolation
from .sequence import build_verified_sequence
from .session import DEFAULT_SLOT, validate_slot


class ReplayCapsuleViolation(ValueError):
    """Raised when a claimed portable replay cannot be rebuilt exactly."""


_SCENARIO_IDENTITIES = {
    ("synthetic_archive", "arrival", "SyntheticArchiveGraph/v1"): "legacy_archive",
    ("archive_gate", "arrival", "ArchiveJourneyGraph/v1"): "three_scene",
    ("station_platform", "platform_arrival", "NightSignalGraph/v1"): "night_signal",
    ("harbor_observatory", "dock_arrival", "HarborProtocolGraph/v1"): "harbor_protocol",
}


@dataclass(frozen=True)
class VerifiedReplayCapsule:
    """One self-contained, audit-friendly projection of a played safe route."""

    capsule_id: str
    scenario: str
    slot_id: str
    graph_revision: str
    timeline_hash: str
    event_count: int
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


def _scenario_for_ledger(ledger: CreativeLedger, graph: StoryGraph) -> str:
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise ReplayCapsuleViolation("Replay capsule requires a story_initialized first event")
    try:
        initial = StoryState.from_dict(ledger.events[0].payload["state"])
    except (KeyError, TypeError, ValueError) as error:
        raise ReplayCapsuleViolation("Replay capsule initial story state is malformed") from error
    scenario = _SCENARIO_IDENTITIES.get((initial.scene_id, initial.beat_id, graph.revision))
    if scenario is None:
        raise ReplayCapsuleViolation("Replay capsule is limited to a registered synthetic scenario identity")
    return scenario


def _require_synthetic_choice_records(ledger: CreativeLedger, graph: StoryGraph) -> None:
    """Reject user-authored labels even when their action IDs are graph-legal.

    ``say`` deliberately persists a bounded caller phrase so the CLI can retain
    its interaction provenance.  A GitHub-safe capsule must not transport that
    phrase, however.  Requiring the canonical graph label gives the exporter a
    mechanical, source-independent proof that every included event originated
    from the fixed synthetic choice surface.
    """

    try:
        entries = replay_timeline(ledger, graph)
    except (TimelineViolation, LedgerViolation, TypeError, ValueError) as error:
        raise ReplayCapsuleViolation("Replay capsule source ledger is not graph-backed") from error
    for entry in entries[1:]:
        event = ledger.events[entry.sequence]
        prior_state = entries[entry.sequence - 1].state
        action = event.payload.get("action")
        if not isinstance(action, Mapping) or entry.action_id is None:
            raise ReplayCapsuleViolation("Replay capsule action provenance is malformed")
        transition = graph.transition_for(prior_state, entry.action_id)
        canonical_action = PlayerAction(entry.action_id, "choice", transition.label).to_dict()
        if canonical_json(dict(action)) != canonical_json(canonical_action):
            raise ReplayCapsuleViolation("Replay capsule rejects caller-authored or non-canonical action text")


def _material_for(ledger: CreativeLedger, slot: str) -> tuple[dict[str, Any], str, StoryGraph]:
    normalized_slot = validate_slot(slot)
    try:
        graph = graph_for_ledger(ledger)
        scenario = _scenario_for_ledger(ledger, graph)
        _require_synthetic_choice_records(ledger, graph)
        timeline = replay_timeline(ledger, graph)
        experience = build_verified_experience(ledger, slot=normalized_slot)
        sequence = build_verified_sequence(ledger, slot=normalized_slot)
        compiled = compile_verified_director(ledger, graph=graph)
        catalog = build_verified_scenario_catalog(scenario)
        coverage = coverage_for_scenario(scenario)
    except ReplayCapsuleViolation:
        raise
    except (TimelineViolation, LedgerViolation, TypeError, ValueError) as error:
        raise ReplayCapsuleViolation("Replay capsule cannot derive a complete verified projection") from error
    if not timeline or not coverage.complete or not compiled.compilation.quality_report.can_generate:
        raise ReplayCapsuleViolation("Replay capsule requires complete route coverage and a passing director gate")
    if experience.timeline_hash != sequence.timeline_hash or experience.timeline_hash != timeline_hash(timeline):
        raise ReplayCapsuleViolation("Replay capsule projections disagree about the source timeline")
    if catalog.graph_revision != graph.revision or catalog.coverage_report_hash != coverage.report_hash:
        raise ReplayCapsuleViolation("Replay capsule scenario catalog is not bound to the played graph")
    material = {
        "schema": "CreativeSyntheticReplayCapsule/v1",
        "status": "synthetic_replay_capsule_verified",
        "scenario": scenario,
        "slot_id": normalized_slot,
        "graph_revision": graph.revision,
        "timeline_hash": timeline_hash(timeline),
        "source": {
            "event_count": len(ledger.events),
            "final_event_id": timeline[-1].event_id,
            "final_state": timeline[-1].state.to_dict(),
            "events": ledger.to_records(),
            "timeline": [entry.to_dict() for entry in timeline],
        },
        "experience": experience.to_dict(),
        "sequence": sequence.to_dict(),
        "director": {
            "verified_input": compiled.verified_input.to_dict(),
            "brief": compiled.compilation.brief.to_dict(),
            "shots": [shot.to_dict() for shot in compiled.compilation.shots],
            "quality_report": compiled.compilation.quality_report.to_dict(),
        },
        "scenario_catalog": catalog.to_dict(),
        "route_coverage": coverage.to_dict(),
        "boundary": {
            "synthetic_only": True,
            "contains_customer_material": False,
            "contains_caller_free_text": False,
            "external_provider_called": False,
            "publication_authorized": False,
            "canonical_knowledge_write": False,
            "client_story_authority": False,
        },
    }
    return material, scenario, graph


def build_verified_replay_capsule(ledger: CreativeLedger, *, slot: str = DEFAULT_SLOT) -> VerifiedReplayCapsule:
    """Build a capsule only after the same runtime-owned checks pass end to end."""

    material, scenario, graph = _material_for(ledger, slot)
    identity_material = {key: value for key, value in material.items() if key != "capsule_id"}
    capsule_id = "capsule_" + hashlib.sha256(canonical_json(identity_material).encode("utf-8")).hexdigest()[:20]
    payload = {**material, "capsule_id": capsule_id}
    return VerifiedReplayCapsule(
        capsule_id=capsule_id,
        scenario=scenario,
        slot_id=str(payload["slot_id"]),
        graph_revision=graph.revision,
        timeline_hash=str(payload["timeline_hash"]),
        event_count=len(ledger.events),
        payload=payload,
    )


def verify_verified_replay_capsule(capsule: Mapping[str, Any]) -> VerifiedReplayCapsule:
    """Rebuild a supplied capsule and reject every altered or unsafe field."""

    try:
        supplied = dict(capsule)
        source = supplied["source"]
        slot = supplied["slot_id"]
        if not isinstance(source, Mapping) or not isinstance(source.get("events"), list):
            raise ReplayCapsuleViolation("Replay capsule source event records are malformed")
        ledger = CreativeLedger.from_records(source["events"])
    except (ReplayCapsuleViolation, LedgerViolation, KeyError, TypeError, ValueError) as error:
        if isinstance(error, ReplayCapsuleViolation):
            raise
        raise ReplayCapsuleViolation("Replay capsule cannot reconstruct its source ledger") from error
    expected = build_verified_replay_capsule(ledger, slot=str(slot))
    if canonical_json(supplied) != canonical_json(expected.to_dict()):
        raise ReplayCapsuleViolation("Replay capsule does not exactly match the verified synthetic replay")
    return expected
