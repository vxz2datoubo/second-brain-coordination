"""Offline AI-director compiler with fail-closed, inspectable quality gates."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .contracts import DirectorBrief, ShotPlan, StoryState, canonical_json


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
    "asset_provenance_missing",
    "asset_provenance_mismatch",
    "skill_activation_mismatch",
    "skill_trigger_reason_mismatch",
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
    metrics: "DirectorQualityMetrics"

    @property
    def can_generate(self) -> bool:
        return not any(finding.severity == "hard" for finding in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_generate": self.can_generate,
            "findings": [finding.to_dict() for finding in self.findings],
            "metrics": self.metrics.to_dict(),
        }


@dataclass(frozen=True)
class DirectorQualityMetrics:
    """Fixed, non-composite measurements for a director compilation."""

    shot_count: int
    total_duration_seconds: int
    hard_finding_count: int
    activated_skill_count: int
    referenced_asset_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "shot_count": self.shot_count,
            "total_duration_seconds": self.total_duration_seconds,
            "hard_finding_count": self.hard_finding_count,
            "activated_skill_count": self.activated_skill_count,
            "referenced_asset_count": self.referenced_asset_count,
        }


@dataclass(frozen=True)
class DirectorCompilation:
    brief: DirectorBrief
    shots: tuple[ShotPlan, ...]
    quality_report: QualityReport


@dataclass(frozen=True)
class DirectorSkill:
    """A narrowly activated directing responsibility, not a prompt blob."""

    skill_id: str
    responsibility: str


DIRECTOR_SKILLS = {
    "scene_continuity": DirectorSkill("scene_continuity", "Maintain scene asset, spatial axis, and adult-character placement."),
    "knowledge_boundary": DirectorSkill("knowledge_boundary", "Show only facts already earned by the story state."),
    "relationship_consequence": DirectorSkill("relationship_consequence", "Express a recorded relationship change through performance, not narration."),
    "handoff_consequence": DirectorSkill("handoff_consequence", "Show the consequence of a documented handoff, meeting, or preserved record."),
}


def select_director_skills(state: StoryState) -> tuple[tuple[str, ...], dict[str, str]]:
    """Select the smallest skill set justified by recorded story state."""

    reasons: dict[str, str] = {
        "scene_continuity": "Every director plan needs the current scene's established spatial axis.",
    }
    if state.known_facts:
        reasons["knowledge_boundary"] = "The state contains earned facts that must not leak beyond character knowledge."
    if any(value != 0 for value in state.relationships.values()):
        reasons["relationship_consequence"] = "The state contains a non-zero recorded relationship consequence."
    if any(key in state.flags for key in {"handoff", "meeting", "record"}):
        reasons["handoff_consequence"] = "The state records a handoff, meeting, or preserved-record consequence."
    return tuple(sorted(reasons)), {key: reasons[key] for key in sorted(reasons)}


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

    def synthetic_asset(**fields: Any) -> dict[str, Any]:
        record = {**fields, "provenance_class": "synthetic_fixture"}
        record["source_hash"] = hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()
        return record

    return {
        "art_scene_synthetic_archive": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_archive_gate": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_interior_archive": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_dawn_courtyard": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_station_platform": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_signal_room": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_archive_vault": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_control_room": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_riverside_dawn": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_harbor_observatory": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_beacon_room": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_map_archive": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_public_forum": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_scene_sunrise_pier": synthetic_asset(role="scene", source="synthetic_fixture"),
        "art_character_mira": synthetic_asset(role="character", name="mira", adult=True, source="synthetic_fixture"),
        "art_character_player": synthetic_asset(role="character", name="player", adult=True, source="synthetic_fixture"),
    }


def _asset_hash_matches(asset: Mapping[str, Any]) -> bool:
    declared = asset.get("source_hash")
    if not isinstance(declared, str) or len(declared) != 64:
        return False
    material = {str(key): value for key, value in asset.items() if key != "source_hash"}
    actual = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return declared == actual


def compile_director_brief(
    state: StoryState,
    *,
    source_timeline_hash: str | None = None,
    story_consequence: Mapping[str, Any] | None = None,
) -> DirectorBrief:
    """Compile only facts already present in StoryState into an auditable brief."""

    spatial_by_scene = {
        "synthetic_archive": ("axis:archive-door-to-courtyard", "mira:left-of-door", "player:right-of-door"),
        "archive_gate": ("axis:archive-gate-to-street", "mira:street-side", "player:gate-side"),
        "interior_archive": ("axis:entry-hall-to-record-room", "mira:left-of-hall", "player:right-of-hall"),
        "dawn_courtyard": ("axis:courtyard-path-to-gate", "mira:gate-side", "player:path-side"),
        "station_platform": ("axis:platform-edge-to-exit", "mira:exit-side", "player:platform-side"),
        "signal_room": ("axis:console-to-door", "mira:door-side", "player:console-side"),
        "archive_vault": ("axis:vault-index-to-threshold", "mira:threshold-side", "player:index-side"),
        "control_room": ("axis:relay-console-to-observation-window", "mira:window-side", "player:console-side"),
        "riverside_dawn": ("axis:river-path-to-street", "mira:street-side", "player:river-side"),
        "harbor_observatory": ("axis:observatory-door-to-pier", "mira:pier-side", "player:door-side"),
        "beacon_room": ("axis:lens-console-to-door", "mira:door-side", "player:console-side"),
        "map_archive": ("axis:chart-index-to-threshold", "mira:threshold-side", "player:index-side"),
        "public_forum": ("axis:forum-table-to-exit", "mira:table-side", "player:exit-side"),
        "sunrise_pier": ("axis:pier-rail-to-street", "mira:street-side", "player:rail-side"),
    }
    spatial_facts = spatial_by_scene.get(state.scene_id, ())
    skill_ids, skill_reasons = select_director_skills(state)
    return DirectorBrief(
        brief_id="brief_" + state.scene_id + "_" + state.beat_id,
        story_state=state,
        character_goals={"mira": "preserve safety and hear the witness", "player": "choose a cautious next step"},
        knowledge_boundaries={"mira": tuple(state.known_facts), "player": tuple(state.known_facts)},
        spatial_facts=spatial_facts,
        content_rating="non_explicit",
        activated_skill_ids=skill_ids,
        skill_trigger_reasons=skill_reasons,
        source_timeline_hash=source_timeline_hash,
        story_consequence=dict(story_consequence or {}),
    )


def _dominant_change(brief: DirectorBrief) -> str:
    consequence = brief.story_consequence
    if not consequence:
        return "the group's confidence shifts after the player action"
    parts: list[str] = []
    if consequence.get("scene_changed"):
        parts.append("the group crosses into a newly earned space")
    facts = consequence.get("new_facts", ())
    if facts:
        parts.append("a newly earned fact changes the next decision")
    relationships = consequence.get("relationship_delta", {})
    if relationships:
        parts.append("a recorded relationship shift changes the performance distance")
    risk_delta = consequence.get("risk_delta", 0)
    if risk_delta:
        parts.append("the risk level visibly changes")
    flags = consequence.get("flag_changes", {})
    if flags:
        parts.append("the documented consequence becomes visible")
    return "; ".join(parts) if parts else "the player action advances the verified story state"


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
            dominant_change=_dominant_change(brief),
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
    if brief.source_timeline_hash is not None and (len(brief.source_timeline_hash) != 64 or not brief.story_consequence):
        findings.append(QualityFinding("knowledge_boundary_violation", "A verified director brief needs a full timeline hash and a recorded final consequence."))
    expected_skill_ids, expected_skill_reasons = select_director_skills(brief.story_state)
    if brief.activated_skill_ids != expected_skill_ids:
        findings.append(QualityFinding("skill_activation_mismatch", "Activated director skills are not the minimal state-justified set."))
    if dict(brief.skill_trigger_reasons) != expected_skill_reasons:
        findings.append(QualityFinding("skill_trigger_reason_mismatch", "Director skill trigger reasons do not match the recorded story state."))
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
                continue
            if asset.get("provenance_class") != "synthetic_fixture":
                findings.append(QualityFinding("asset_provenance_mismatch", f"{artifact_id} is outside this offline synthetic asset authority."))
            elif not _asset_hash_matches(asset):
                findings.append(QualityFinding("asset_provenance_missing", f"{artifact_id} lacks a valid stable source hash."))
            if artifact_id.startswith("art_scene_") and artifact_id != expected_scene_asset:
                findings.append(QualityFinding("scene_reference_mismatch", f"{shot.shot_id} references a scene outside the current story state."))
            elif artifact_id.startswith("art_scene_") and asset.get("role") != "scene":
                findings.append(QualityFinding("scene_reference_mismatch", f"{artifact_id} is not registered as a scene asset."))
            if asset.get("role") == "character" and asset.get("adult") is not True:
                findings.append(QualityFinding("identity_not_adult", f"Character asset is not confirmed adult: {artifact_id}"))
    return QualityReport(
        tuple(findings),
        DirectorQualityMetrics(
            shot_count=len(shots),
            total_duration_seconds=sum(shot.duration_seconds for shot in shots),
            hard_finding_count=sum(1 for finding in findings if finding.severity == "hard"),
            activated_skill_count=len(brief.activated_skill_ids),
            referenced_asset_count=len({artifact_id for shot in shots for artifact_id in shot.reference_artifact_ids}),
        ),
    )


def compile_director(
    state: StoryState,
    assets: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    source_timeline_hash: str | None = None,
    story_consequence: Mapping[str, Any] | None = None,
) -> DirectorCompilation:
    brief = compile_director_brief(
        state,
        source_timeline_hash=source_timeline_hash,
        story_consequence=story_consequence,
    )
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
        compilation=compile_director(
            verified_input.state,
            assets,
            source_timeline_hash=verified_input.timeline_hash,
            story_consequence=verified_input.final_consequence,
        ),
        verified_input=verified_input,
    )
