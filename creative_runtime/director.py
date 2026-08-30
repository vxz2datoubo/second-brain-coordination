"""Offline AI-director compiler with fail-closed, inspectable quality gates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import DirectorBrief, ShotPlan, StoryState


HARD_CODES = {
    "missing_asset",
    "identity_not_adult",
    "spatial_axis_missing",
    "spatial_axis_mismatch",
    "knowledge_boundary_violation",
    "content_rating_violation",
    "duration_infeasible",
    "duration_budget_exceeded",
    "dominant_change_missing",
    "performance_task_missing",
    "duplicate_shot_id",
    "shot_beat_mismatch",
    "scene_reference_missing",
    "scene_reference_mismatch",
    "character_reference_missing",
}


@dataclass(frozen=True)
class QualityFinding:
    code: str
    message: str
    severity: str = "hard"

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass(frozen=True)
class QualityReport:
    findings: tuple[QualityFinding, ...]

    @property
    def can_generate(self) -> bool:
        return not any(finding.severity == "hard" for finding in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {"can_generate": self.can_generate, "findings": [finding.to_dict() for finding in self.findings]}


@dataclass(frozen=True)
class DirectorCompilation:
    brief: DirectorBrief
    shots: tuple[ShotPlan, ...]
    quality_report: QualityReport


@dataclass(frozen=True)
class VerifiedDirectorCompilation:
    """A compilation whose state is tied to a validated timeline prefix.

    `compile_director` intentionally remains a pure state-to-plan function for
    unit use. Production-facing callers should use this wrapper so the director
    does not receive a state that bypassed narrative continuity validation.
    """

    compilation: DirectorCompilation
    verified_input: Any


def synthetic_asset_index() -> dict[str, dict[str, Any]]:
    """Synthetic index; an external index must arrive through a provenance gate."""

    return {
        "art_scene_synthetic_archive": {"role": "scene", "source": "synthetic_fixture"},
        "art_scene_archive_gate": {"role": "scene", "source": "synthetic_fixture"},
        "art_scene_interior_archive": {"role": "scene", "source": "synthetic_fixture"},
        "art_scene_dawn_courtyard": {"role": "scene", "source": "synthetic_fixture"},
        "art_character_mira": {"role": "character", "name": "mira", "adult": True, "source": "synthetic_fixture"},
        "art_character_player": {"role": "character", "name": "player", "adult": True, "source": "synthetic_fixture"},
    }


def compile_director_brief(state: StoryState) -> DirectorBrief:
    """Compile only facts already present in StoryState into an auditable brief."""

    spatial_by_scene = {
        "synthetic_archive": ("axis:archive-door-to-courtyard", "mira:left-of-door", "player:right-of-door"),
        "archive_gate": ("axis:archive-gate-to-street", "mira:street-side", "player:gate-side"),
        "interior_archive": ("axis:entry-hall-to-record-room", "mira:left-of-hall", "player:right-of-hall"),
        "dawn_courtyard": ("axis:courtyard-path-to-gate", "mira:gate-side", "player:path-side"),
    }
    spatial_facts = spatial_by_scene.get(state.scene_id, ())
    return DirectorBrief(
        brief_id="brief_" + state.scene_id + "_" + state.beat_id,
        story_state=state,
        character_goals={"mira": "preserve safety and hear the witness", "player": "choose a cautious next step"},
        knowledge_boundaries={"mira": tuple(state.known_facts), "player": tuple(state.known_facts)},
        spatial_facts=spatial_facts,
        content_rating="non_explicit",
    )


def compile_shots(brief: DirectorBrief) -> tuple[ShotPlan, ...]:
    scene_id = brief.story_state.scene_id
    axis = next((item.removeprefix("axis:") for item in brief.spatial_facts if item.startswith("axis:")), "")
    return (
        ShotPlan(
            shot_id="shot_" + brief.story_state.beat_id + "_01",
            beat_id=brief.story_state.beat_id,
            shot_role="spatial orientation",
            camera="wide two-shot, establish the scene axis before the choice consequence",
            performance_task="Mira checks the space while the player holds a deliberate pause.",
            duration_seconds=5,
            reference_artifact_ids=("art_scene_" + scene_id, "art_character_mira", "art_character_player"),
            axis=axis,
            lighting="motivated practical light establishes the playable space",
            sound="environmental room tone establishes location and distance",
            dominant_change="the audience understands where each adult character stands",
        ),
        ShotPlan(
            shot_id="shot_" + brief.story_state.beat_id + "_02",
            beat_id=brief.story_state.beat_id,
            shot_role="decision consequence",
            camera="medium two-shot, hold the established scene axis",
            performance_task="Mira listens, then marks a deliberate choice.",
            duration_seconds=8,
            reference_artifact_ids=("art_scene_" + scene_id, "art_character_mira", "art_character_player"),
            axis=axis,
            lighting="motivated practical light with a readable change in depth",
            sound="environmental room tone and the consequence of the player choice",
            dominant_change="the group's confidence shifts after the player action",
        ),
    )


def validate_compilation(
    brief: DirectorBrief,
    shots: tuple[ShotPlan, ...],
    assets: Mapping[str, Mapping[str, Any]],
) -> QualityReport:
    findings: list[QualityFinding] = []
    if brief.content_rating != "non_explicit":
        findings.append(QualityFinding("content_rating_violation", "Only non_explicit content is permitted."))
    if not any(item.startswith("axis:") for item in brief.spatial_facts):
        findings.append(QualityFinding("spatial_axis_missing", "Brief omits a spatial axis."))
    known = set(brief.story_state.known_facts)
    expected_axis = next((item.removeprefix("axis:") for item in brief.spatial_facts if item.startswith("axis:")), "")
    expected_scene_asset = "art_scene_" + brief.story_state.scene_id
    if len({shot.shot_id for shot in shots}) != len(shots):
        findings.append(QualityFinding("duplicate_shot_id", "Shot identifiers must be unique within a director compilation."))
    if sum(shot.duration_seconds for shot in shots) > 20:
        findings.append(QualityFinding("duration_budget_exceeded", "Total planned duration must not exceed 20 seconds."))
    for character, facts in brief.knowledge_boundaries.items():
        for fact in facts:
            if fact not in known:
                findings.append(QualityFinding("knowledge_boundary_violation", f"{character} is assigned an unknown fact."))
    for shot in shots:
        if shot.beat_id != brief.story_state.beat_id:
            findings.append(QualityFinding("shot_beat_mismatch", f"{shot.shot_id} is not assigned to the current story beat."))
        if not shot.axis:
            findings.append(QualityFinding("spatial_axis_missing", f"{shot.shot_id} has no axis."))
        elif not expected_axis or shot.axis != expected_axis:
            findings.append(QualityFinding("spatial_axis_mismatch", f"{shot.shot_id} does not hold the brief's spatial axis."))
        if not 1 <= shot.duration_seconds <= 20:
            findings.append(QualityFinding("duration_infeasible", f"{shot.shot_id} duration must be 1-20 seconds."))
        if not shot.dominant_change:
            findings.append(QualityFinding("dominant_change_missing", f"{shot.shot_id} has no dominant change."))
        if not shot.performance_task:
            findings.append(QualityFinding("performance_task_missing", f"{shot.shot_id} has no performance task."))
        if expected_scene_asset not in shot.reference_artifact_ids:
            findings.append(QualityFinding("scene_reference_missing", f"{shot.shot_id} does not reference the current scene asset."))
        required_characters = {"art_character_mira", "art_character_player"}
        if not required_characters <= set(shot.reference_artifact_ids):
            findings.append(QualityFinding("character_reference_missing", f"{shot.shot_id} lacks a required adult character reference."))
        for artifact_id in shot.reference_artifact_ids:
            asset = assets.get(artifact_id)
            if asset is None:
                findings.append(QualityFinding("missing_asset", f"Missing reference asset: {artifact_id}"))
            elif artifact_id.startswith("art_scene_") and artifact_id != expected_scene_asset:
                findings.append(QualityFinding("scene_reference_mismatch", f"{shot.shot_id} references a scene outside the current story state."))
            elif artifact_id.startswith("art_scene_") and asset.get("role") != "scene":
                findings.append(QualityFinding("scene_reference_mismatch", f"{artifact_id} is not registered as a scene asset."))
            elif asset.get("role") == "character" and asset.get("adult") is not True:
                findings.append(QualityFinding("identity_not_adult", f"Character asset is not confirmed adult: {artifact_id}"))
    return QualityReport(tuple(findings))


def compile_director(state: StoryState, assets: Mapping[str, Mapping[str, Any]] | None = None) -> DirectorCompilation:
    brief = compile_director_brief(state)
    shots = compile_shots(brief)
    report = validate_compilation(brief, shots, assets if assets is not None else synthetic_asset_index())
    return DirectorCompilation(brief=brief, shots=shots, quality_report=report)


def compile_verified_director(
    ledger: Any,
    assets: Mapping[str, Mapping[str, Any]] | None = None,
    graph: Any | None = None,
) -> VerifiedDirectorCompilation:
    """Compile only after all ledger prefixes pass graph-backed replay.

    Imports are local to preserve the simple contract/ledger/director dependency
    direction and to make a semantic timeline failure stop before any director
    plan is emitted.
    """

    from .continuity import verified_director_input

    verified_input = verified_director_input(ledger, graph)
    return VerifiedDirectorCompilation(
        compilation=compile_director(verified_input.state, assets),
        verified_input=verified_input,
    )
