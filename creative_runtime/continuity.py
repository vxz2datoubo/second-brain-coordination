"""Deterministic director-continuity diagnostics over the truthful event-prefix timeline.

This module has no media-generation or story-mutation authority. It compiles existing
offline director packets and emits stable diagnostics only.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .contracts import ShotPlan, StoryState, canonical_json
from .director import DirectorCompilation, compile_director, synthetic_asset_index
from .ledger import CreativeLedger
from .scene_graph import SceneGraph
from .timeline import build_prefix_timeline


HARD_CONTINUITY_CODES = {
    "action_causality_violation",
    "duration_budget_exceeded",
    "identity_continuity_violation",
    "knowledge_reveal_order_violation",
    "packet_quality_failure",
    "screen_direction_violation",
    "spatial_relation_violation",
}


@dataclass(frozen=True)
class ContinuityDiagnostic:
    code: str
    severity: str
    locator: str
    observed: str
    expected: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "locator": self.locator,
            "observed": self.observed,
            "expected": self.expected,
        }


@dataclass(frozen=True)
class DirectedBeat:
    index: int
    event_type: str
    state: StoryState
    action_id: str | None
    transition_id: str | None
    revealed_facts: tuple[str, ...]

    @property
    def locator(self) -> str:
        return f"beat[{self.index}]/{self.state.scene_id}/{self.state.beat_id}"


@dataclass(frozen=True)
class DirectorSequence:
    beats: tuple[DirectedBeat, ...]
    packets: tuple[DirectorCompilation, ...]
    diagnostics: tuple[ContinuityDiagnostic, ...]
    duration_budget_seconds: int

    @property
    def can_generate(self) -> bool:
        """Quality/continuity readiness only; this module has no generation call path."""

        return not any(item.severity == "hard" for item in self.diagnostics)

    @property
    def final_state_handoff(self) -> dict[str, Any]:
        state = self.beats[-1].state
        serialized = state.to_dict()
        return {
            "scene_id": state.scene_id,
            "beat_id": state.beat_id,
            "state": serialized,
            "state_digest": hashlib.sha256(canonical_json(serialized).encode("utf-8")).hexdigest(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_generate": self.can_generate,
            "duration_budget_seconds": self.duration_budget_seconds,
            "final_state_handoff": self.final_state_handoff,
            "cross_cut_contract": [
                {
                    "from": self.beats[index - 1].locator,
                    "to": beat.locator,
                    "event_type": beat.event_type,
                    "action_id": beat.action_id,
                    "transition_id": beat.transition_id,
                }
                for index, beat in enumerate(self.beats)
                if index
            ],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


def directed_beats_from_ledger(ledger: CreativeLedger, graph: SceneGraph) -> tuple[DirectedBeat, ...]:
    """Derive ordered director inputs from the same exact-prefix truth used by S08."""

    timeline = build_prefix_timeline(ledger, graph)
    beats: list[DirectedBeat] = []
    for index, entry in enumerate(timeline):
        event = ledger.events[index]
        revealed: tuple[str, ...] = ()
        if event.event_type == "player_action":
            patch = event.payload.get("resulting_patch", {})
            if isinstance(patch, Mapping):
                revealed = tuple(str(item) for item in patch.get("reveal_facts", ()))
        beats.append(
            DirectedBeat(
                index=index,
                event_type=event.event_type,
                state=entry.state,
                action_id=entry.action_id,
                transition_id=entry.transition_id,
                revealed_facts=revealed,
            )
        )
    return tuple(beats)


def _character_references(shot: ShotPlan, assets: Mapping[str, Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(assets[artifact_id].get("name", artifact_id))
            for artifact_id in shot.reference_artifact_ids
            if assets.get(artifact_id, {}).get("role") == "character"
        )
    )


def validate_sequence(
    beats: tuple[DirectedBeat, ...],
    packets: tuple[DirectorCompilation, ...],
    assets: Mapping[str, Mapping[str, Any]],
    duration_budget_seconds: int,
) -> tuple[ContinuityDiagnostic, ...]:
    """Return deterministic diagnostics; never rewrite the ledger, graph, or packets."""

    if not beats or len(beats) != len(packets):
        raise ValueError("Directed beats and packets must be non-empty and aligned")
    diagnostics: list[ContinuityDiagnostic] = []
    total_duration = 0
    prior_axis: str | None = None
    prior_characters: tuple[str, ...] | None = None
    known_facts = set(beats[0].state.known_facts)

    for beat, packet in zip(beats, packets, strict=True):
        if not packet.quality_report.can_generate:
            diagnostics.append(
                ContinuityDiagnostic(
                    "packet_quality_failure",
                    "hard",
                    beat.locator,
                    ",".join(finding.code for finding in packet.quality_report.findings),
                    "packet quality report without hard findings",
                )
            )
        expected_axis = next(
            (fact.removeprefix("axis:") for fact in packet.brief.spatial_facts if fact.startswith("axis:")),
            "",
        )
        for shot in packet.shots:
            locator = f"{beat.locator}/shot:{shot.shot_id}"
            total_duration += shot.duration_seconds
            if shot.axis != expected_axis:
                diagnostics.append(
                    ContinuityDiagnostic(
                        "spatial_relation_violation",
                        "hard",
                        locator,
                        shot.axis,
                        expected_axis or "brief spatial axis",
                    )
                )
            if prior_axis is not None and shot.axis != prior_axis:
                diagnostics.append(
                    ContinuityDiagnostic(
                        "screen_direction_violation",
                        "hard",
                        locator,
                        shot.axis,
                        prior_axis,
                    )
                )
            prior_axis = shot.axis
            characters = _character_references(shot, assets)
            if prior_characters is not None and characters != prior_characters:
                diagnostics.append(
                    ContinuityDiagnostic(
                        "identity_continuity_violation",
                        "hard",
                        locator,
                        ",".join(characters),
                        ",".join(prior_characters),
                    )
                )
            prior_characters = characters

        if beat.index:
            previous = beats[beat.index - 1]
            introduced = set(beat.state.known_facts) - known_facts
            if beat.event_type == "player_action":
                unsupported = introduced - set(beat.revealed_facts)
                if unsupported:
                    diagnostics.append(
                        ContinuityDiagnostic(
                            "knowledge_reveal_order_violation",
                            "hard",
                            beat.locator,
                            ",".join(sorted(unsupported)),
                            "facts declared by the incoming transition reveal_facts",
                        )
                    )
                if not beat.action_id or not beat.transition_id:
                    diagnostics.append(
                        ContinuityDiagnostic(
                            "action_causality_violation",
                            "hard",
                            beat.locator,
                            f"action={beat.action_id!r}, transition={beat.transition_id!r}",
                            "declared graph-backed action and transition",
                        )
                    )
                if previous.state == beat.state:
                    diagnostics.append(
                        ContinuityDiagnostic(
                            "action_causality_violation",
                            "hard",
                            beat.locator,
                            "state unchanged",
                            "declared state consequence",
                        )
                    )
            elif introduced:
                diagnostics.append(
                    ContinuityDiagnostic(
                        "knowledge_reveal_order_violation",
                        "hard",
                        beat.locator,
                        ",".join(sorted(introduced)),
                        "maintenance state_patch may not mint unrevealed knowledge",
                    )
                )
            known_facts.update(beat.state.known_facts)

    if total_duration > duration_budget_seconds:
        diagnostics.append(
            ContinuityDiagnostic(
                "duration_budget_exceeded",
                "hard",
                "sequence/duration",
                str(total_duration),
                str(duration_budget_seconds),
            )
        )
    return tuple(diagnostics)


def compile_director_sequence(
    ledger: CreativeLedger,
    graph: SceneGraph,
    assets: Mapping[str, Mapping[str, Any]] | None = None,
    duration_budget_seconds: int = 90,
) -> DirectorSequence:
    """Compile ordered offline packets and diagnostics with no generation authority."""

    source_assets = assets if assets is not None else synthetic_asset_index()
    beats = directed_beats_from_ledger(ledger, graph)
    packets = tuple(compile_director(beat.state, source_assets) for beat in beats)
    diagnostics = validate_sequence(beats, packets, source_assets, duration_budget_seconds)
    return DirectorSequence(beats, packets, diagnostics, duration_budget_seconds)
