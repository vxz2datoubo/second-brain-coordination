"""Verified multi-beat director sequences for interactive-film replay."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .continuity import TimelineViolation, graph_for_ledger, replay_timeline, timeline_hash
from .contracts import canonical_json
from .director import compile_verified_director
from .ledger import CreativeLedger
from .presentation import PresentationViolation, build_interactive_frame
from .session import DEFAULT_SLOT, validate_slot


class SequenceViolation(ValueError):
    """Raised when a whole-film plan cannot be derived from verified prefixes."""


@dataclass(frozen=True)
class VerifiedSequencePlan:
    sequence_id: str
    slot_id: str
    graph_revision: str
    timeline_hash: str
    steps: tuple[Mapping[str, Any], ...]
    total_duration_seconds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "VerifiedInteractiveSequencePlan/v1",
            "status": "sequence_plan_verified",
            "sequence_id": self.sequence_id,
            "slot_id": self.slot_id,
            "graph_revision": self.graph_revision,
            "timeline_hash": self.timeline_hash,
            "steps": [dict(step) for step in self.steps],
            "total_duration_seconds": self.total_duration_seconds,
            "provenance": {
                "synthetic_only": True,
                "customer_data_present": False,
                "external_provider_called": False,
                "client_story_authority": False,
            },
        }


def build_verified_sequence(ledger: CreativeLedger, *, slot: str = DEFAULT_SLOT) -> VerifiedSequencePlan:
    """Compile a render-order plan from independently replayed ledger prefixes."""

    normalized_slot = validate_slot(slot)
    try:
        graph = graph_for_ledger(ledger)
        timeline = replay_timeline(ledger, graph)
    except (TimelineViolation, TypeError, ValueError) as error:
        raise SequenceViolation("Sequence requires a complete verified story timeline") from error
    steps: list[Mapping[str, Any]] = []
    prior_state: Mapping[str, Any] | None = None
    for index, entry in enumerate(timeline):
        prefix = CreativeLedger(ledger.events[: index + 1])
        try:
            frame = build_interactive_frame(prefix, slot=normalized_slot).to_dict()
        except PresentationViolation as error:
            raise SequenceViolation("Sequence prefix has no verified presentation frame") from error
        compiled = compile_verified_director(prefix, graph=graph)
        if not compiled.compilation.quality_report.can_generate:
            raise SequenceViolation("Sequence prefix is blocked by director quality gate")
        if frame["timeline_hash"] != compiled.verified_input.timeline_hash:
            raise SequenceViolation("Sequence frame and director prefix identities diverge")
        scene_changed = prior_state is not None and prior_state.get("scene_id") != entry.state.scene_id
        cut_policy = "establish_initial_space" if index == 0 else "reestablish_after_scene_change" if scene_changed else "hold_verified_axis"
        shots = [shot.to_dict() for shot in compiled.compilation.shots]
        if not shots:
            raise SequenceViolation("Sequence prefix has no director shots")
        steps.append({
            "sequence_index": index,
            "event_id": entry.event_id,
            "action_id": entry.action_id,
            "transition_id": entry.transition_id,
            "timeline_hash": frame["timeline_hash"],
            "frame_id": frame["frame_id"],
            "state": entry.state.to_dict(),
            "consequence": dict(entry.consequence),
            "cut_policy": cut_policy,
            "shots": shots,
            "duration_seconds": sum(shot["duration_seconds"] for shot in shots),
        })
        prior_state = entry.state.to_dict()
    material = {
        "schema": "VerifiedInteractiveSequencePlan/v1",
        "slot_id": normalized_slot,
        "graph_revision": graph.revision,
        "timeline_hash": timeline_hash(timeline),
        "steps": steps,
    }
    return VerifiedSequencePlan(
        sequence_id="sequence_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20],
        slot_id=normalized_slot,
        graph_revision=graph.revision,
        timeline_hash=timeline_hash(timeline),
        steps=tuple(steps),
        total_duration_seconds=sum(int(step["duration_seconds"]) for step in steps),
    )
