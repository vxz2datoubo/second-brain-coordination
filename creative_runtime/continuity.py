"""Deterministic multi-beat director continuity checks without generation authority."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from .contracts import ShotPlan, StoryState, canonical_json
from .director import DirectorCompilation, compile_director, synthetic_asset_index
from .ledger import CreativeLedger
from .scene_graph import SceneGraph, SceneGraphViolation


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
        return not any(item.severity == "hard" for item in self.diagnostics)

    @property
    def final_state_handoff(self) -> dict[str, Any]:
        state = self.beats[-1].state
        return {
            "scene_id": state.scene_id,
            "beat_id": state.beat_id,
            "state": state.to_dict(),
            "state_digest": canonical_json(state.to_dict()),
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
                    "action_id": beat.action_id,
                    "transition_id": beat.transition_id,
                }
                for index, beat in enumerate(self.beats)
                if index
            ],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


def directed_beats_from_ledger(ledger: CreativeLedger, graph: SceneGraph) -> tuple[DirectedBeat, ...]:
    """Reconstruct graph-backed causal inputs from the canonical event ledger."""

    initial = ledger.replay() if len(ledger.events) == 1 else StoryState.from_dict(ledger.events[0].payload["state"])
    graph.beat_for(initial)
    beats = [DirectedBeat(0, initial, None, None, tuple(initial.known_facts))]
    state = initial
    for index, event in enumerate(ledger.events[1:], start=1):
        if event.event_type != "player_action":
            raise SceneGraphViolation("Director continuity only accepts player_action events after initialization")
        action_record = event.payload.get("action", {})
        action_id = str(action_record.get("action_id", ""))
        next_state, action = graph.apply(state, action_id)
        recorded_transition = event.payload.get("transition_id")
        recorded_patch = event.payload.get("resulting_patch")
        expected_patch = {**action.patch, "scene_id": next_state.scene_id, "beat_id": next_state.beat_id}
        if recorded_transition != action.transition_id or recorded_patch != expected_patch:
            raise SceneGraphViolation(f"Ledger action causality does not match manifest at event {event.sequence}")
        revealed = tuple(str(item) for item in action.patch.get("reveal_facts", ()))
        beats.append(DirectedBeat(index, next_state, action_id, action.transition_id, revealed))
        state = next_state
    return tuple(beats)


def _character_references(shot: ShotPlan, assets: Mapping[str, Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(sorted(
        str(assets[artifact_id].get("name", artifact_id))
        for artifact_id in shot.reference_artifact_ids
        if assets.get(artifact_id, {}).get("role") == "character"
    ))


def validate_sequence(
    beats: tuple[DirectedBeat, ...],
    packets: tuple[DirectorCompilation, ...],
    assets: Mapping[str, Mapping[str, Any]],
    duration_budget_seconds: int,
) -> tuple[ContinuityDiagnostic, ...]:
    if not beats or len(beats) != len(packets):
        raise ValueError("Directed beats and packets must be non-empty and aligned")
    diagnostics: list[ContinuityDiagnostic] = []
    total_duration = 0
    prior_axis: str | None = None
    prior_characters: tuple[str, ...] | None = None
    known_facts = set(beats[0].state.known_facts)
    for beat, packet in zip(beats, packets, strict=True):
        if not packet.quality_report.can_generate:
            diagnostics.append(ContinuityDiagnostic(
                "packet_quality_failure", "hard", beat.locator,
                ",".join(finding.code for finding in packet.quality_report.findings),
                "packet quality report without hard findings",
            ))
        expected_axis = next((fact.removeprefix("axis:") for fact in packet.brief.spatial_facts if fact.startswith("axis:")), "")
        for shot in packet.shots:
            locator = f"{beat.locator}/shot:{shot.shot_id}"
            total_duration += shot.duration_seconds
            if shot.axis != expected_axis:
                diagnostics.append(ContinuityDiagnostic(
                    "spatial_relation_violation", "hard", locator, shot.axis, expected_axis or "brief spatial axis",
                ))
            if prior_axis is not None and shot.axis != prior_axis:
                diagnostics.append(ContinuityDiagnostic(
                    "screen_direction_violation", "hard", locator, shot.axis, prior_axis,
                ))
            prior_axis = shot.axis
            characters = _character_references(shot, assets)
            if prior_characters is not None and characters != prior_characters:
                diagnostics.append(ContinuityDiagnostic(
                    "identity_continuity_violation", "hard", locator, ",".join(characters), ",".join(prior_characters),
                ))
            prior_characters = characters
        if beat.index:
            previous = beats[beat.index - 1]
            introduced = set(beat.state.known_facts) - known_facts
            unsupported = introduced - set(beat.revealed_facts)
            if unsupported:
                diagnostics.append(ContinuityDiagnostic(
                    "knowledge_reveal_order_violation", "hard", beat.locator, ",".join(sorted(unsupported)),
                    "facts declared by the incoming transition reveal_facts",
                ))
            if not beat.action_id or not beat.transition_id:
                diagnostics.append(ContinuityDiagnostic(
                    "action_causality_violation", "hard", beat.locator,
                    f"action={beat.action_id!r}, transition={beat.transition_id!r}", "declared graph-backed action and transition",
                ))
            if previous.state == beat.state:
                diagnostics.append(ContinuityDiagnostic(
                    "action_causality_violation", "hard", beat.locator, "state unchanged", "declared state consequence",
                ))
            known_facts.update(beat.revealed_facts)
    if total_duration > duration_budget_seconds:
        diagnostics.append(ContinuityDiagnostic(
            "duration_budget_exceeded", "hard", "sequence/duration", str(total_duration), str(duration_budget_seconds),
        ))
    return tuple(diagnostics)


def compile_director_sequence(
    ledger: CreativeLedger,
    graph: SceneGraph,
    assets: Mapping[str, Mapping[str, Any]] | None = None,
    duration_budget_seconds: int = 90,
) -> DirectorSequence:
    """Compile ordered existing director packets; diagnostics have no mutation/generation path."""

    source_assets = assets if assets is not None else synthetic_asset_index()
    beats = directed_beats_from_ledger(ledger, graph)
    packets = tuple(compile_director(beat.state, source_assets) for beat in beats)
    diagnostics = validate_sequence(beats, packets, source_assets, duration_budget_seconds)
    return DirectorSequence(beats, packets, diagnostics, duration_budget_seconds)


def replace_packet_shots(packet: DirectorCompilation, shots: tuple[ShotPlan, ...]) -> DirectorCompilation:
    """Test-only ergonomic helper; it does not change any story or director authority."""

    return replace(packet, shots=shots)
