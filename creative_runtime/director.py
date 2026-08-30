"""Offline AI-director compiler with fail-closed, inspectable quality gates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import DirectorBrief, ShotPlan, StoryState


HARD_CODES = {
    "missing_asset",
    "identity_not_adult",
    "spatial_axis_missing",
    "knowledge_boundary_violation",
    "content_rating_violation",
    "duration_infeasible",
    "dominant_change_missing",
    "performance_task_missing",
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
        "art_character_mira": {"role": "character", "name": "mira", "adult": True, "source": "synthetic_fixture"},
        "art_character_player": {"role": "character", "name": "player", "adult": True, "source": "synthetic_fixture"},
    }


def compile_director_brief(state: StoryState) -> DirectorBrief:
    """Compile only facts already present in StoryState into an auditable brief."""

    return DirectorBrief(
        brief_id="brief_" + state.scene_id + "_" + state.beat_id,
        story_state=state,
        character_goals={"mira": "preserve safety and hear the witness", "player": "choose a cautious next step"},
        knowledge_boundaries={"mira": tuple(state.known_facts), "player": tuple(state.known_facts)},
        spatial_facts=("axis:archive-door-to-courtyard", "mira:left-of-door", "player:right-of-door"),
        content_rating="non_explicit",
    )


def compile_shots(brief: DirectorBrief) -> tuple[ShotPlan, ...]:
    return (
        ShotPlan(
            shot_id="shot_" + brief.story_state.beat_id + "_01",
            beat_id=brief.story_state.beat_id,
            shot_role="decision consequence",
            camera="medium two-shot, hold the door axis",
            performance_task="Mira listens, then marks a deliberate choice.",
            duration_seconds=8,
            reference_artifact_ids=("art_scene_synthetic_archive", "art_character_mira", "art_character_player"),
            axis="archive-door-to-courtyard",
            lighting="rain reflection outside, practical archive light inside",
            sound="rain, hinge, distant room tone",
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
    for character, facts in brief.knowledge_boundaries.items():
        for fact in facts:
            if fact not in known:
                findings.append(QualityFinding("knowledge_boundary_violation", f"{character} is assigned an unknown fact."))
    for shot in shots:
        if not shot.axis:
            findings.append(QualityFinding("spatial_axis_missing", f"{shot.shot_id} has no axis."))
        if not 1 <= shot.duration_seconds <= 20:
            findings.append(QualityFinding("duration_infeasible", f"{shot.shot_id} duration must be 1-20 seconds."))
        if not shot.dominant_change:
            findings.append(QualityFinding("dominant_change_missing", f"{shot.shot_id} has no dominant change."))
        if not shot.performance_task:
            findings.append(QualityFinding("performance_task_missing", f"{shot.shot_id} has no performance task."))
        for artifact_id in shot.reference_artifact_ids:
            asset = assets.get(artifact_id)
            if asset is None:
                findings.append(QualityFinding("missing_asset", f"Missing reference asset: {artifact_id}"))
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
