"""Provider-neutral immutable ShotBundle/v1 compiler."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from typing import Any

from .contracts import canonical_json
from .director_beat_plan import DirectorBeatPlan, DirectorBeatPlanner, DirectorOutcomePreview


ALLOWED_FRAMING = frozenset({"wide", "medium", "close", "insert", "two_shot", "over_shoulder"})
ALLOWED_MOVEMENT = frozenset({"locked", "dolly", "pan", "track", "handheld_restrained"})


class ShotBundleViolation(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ShotResponsibility:
    shot_id: str
    order: int
    responsibility: str
    covered_beat_ids: tuple[str, ...]
    framing: str
    subject_ids: tuple[str, ...]
    spatial_anchor: str
    staging_references: tuple[str, ...]
    movement_intent: str
    min_duration_seconds: int
    max_duration_seconds: int
    continuity_anchors: tuple[str, ...]
    dialogue_audio_responsibility: str
    asset_role_references: tuple[str, ...]
    option_ids: tuple[str, ...] = ()
    schema_version: str = "ShotResponsibility/v1"

    def to_dict(self) -> dict[str, Any]:
        return {name: (list(value) if isinstance(value, tuple) else value)
                for name, value in vars(self).items()}


@dataclass(frozen=True)
class ShotBundle:
    bundle_id: str
    bundle_hash: str
    script_id: str
    script_revision: str
    package_hash: str
    director_brief_compile_hash: str
    graph_hash: str
    bible_hash: str
    director_beat_plan_hash: str
    style_profile_id: str
    choice_id: str
    scene_id: str
    selected_outcome_preview_hash: str | None
    shots: tuple[ShotResponsibility, ...]
    schema_version: str = "ShotBundle/v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "script_id": self.script_id,
            "script_revision": self.script_revision,
            "package_hash": self.package_hash,
            "director_brief_compile_hash": self.director_brief_compile_hash,
            "graph_hash": self.graph_hash,
            "bible_hash": self.bible_hash,
            "director_beat_plan_hash": self.director_beat_plan_hash,
            "style_profile_id": self.style_profile_id,
            "choice_id": self.choice_id,
            "scene_id": self.scene_id,
            "selected_outcome_preview_hash": self.selected_outcome_preview_hash,
            "shots": [item.to_dict() for item in self.shots],
        }


def _material(bundle: ShotBundle) -> dict[str, Any]:
    value = bundle.to_dict()
    value.pop("bundle_id")
    value.pop("bundle_hash")
    return value


def _shot(plan: DirectorBeatPlan, order: int, role: str, beat_orders: tuple[int, ...],
          framing: str, movement: str, audio: str, *, option_ids: tuple[str, ...] = ()) -> ShotResponsibility:
    beat_ids = tuple(plan.beats[index - 1].beat_id for index in beat_orders)
    subjects = tuple(item.removeprefix("character_").removesuffix("_v1")
                     for item in plan.character_anchor_asset_ids)
    assets = (f"scene_anchor:{plan.scene_anchor_asset_id}",) + tuple(
        f"character_anchor:{item}" for item in plan.character_anchor_asset_ids
    )
    return ShotResponsibility(
        f"{plan.choice_id}:shot:{order:02d}", order, role, beat_ids, framing, subjects,
        plan.scene_anchor_asset_id, tuple(plan.beats[index - 1].constraints[0] for index in beat_orders),
        movement, 2, 8, (plan.scene_anchor_asset_id, *plan.character_anchor_asset_ids), audio, assets,
        option_ids,
    )


def validate_shot_bundle(bundle: ShotBundle, plan: DirectorBeatPlan) -> ShotBundle:
    if bundle.schema_version != "ShotBundle/v1":
        raise ShotBundleViolation("BUNDLE_SCHEMA", "unsupported ShotBundle schema")
    identity = (plan.script_id, plan.script_revision, plan.package_hash, plan.director_brief_compile_hash,
                plan.graph_hash, plan.bible_hash, plan.plan_hash, plan.style_profile_id, plan.choice_id, plan.scene_id)
    actual = (bundle.script_id, bundle.script_revision, bundle.package_hash, bundle.director_brief_compile_hash,
              bundle.graph_hash, bundle.bible_hash, bundle.director_beat_plan_hash, bundle.style_profile_id,
              bundle.choice_id, bundle.scene_id)
    if actual != identity:
        raise ShotBundleViolation("SOURCE_IDENTITY", "bundle and plan identity differ")
    if bundle.bundle_hash != _digest(_material(bundle)) or bundle.bundle_id != f"shotbundle_{bundle.bundle_hash[:24]}":
        raise ShotBundleViolation("BUNDLE_HASH", "bundle hash or ID is stale")
    ids = [item.shot_id for item in bundle.shots]
    if not ids or len(ids) != len(set(ids)):
        raise ShotBundleViolation("SHOT_ID", "shot IDs must be present and unique")
    if [item.order for item in bundle.shots] != list(range(1, len(bundle.shots) + 1)):
        raise ShotBundleViolation("SHOT_ORDER", "shot order must be contiguous")
    covered = {beat_id for item in bundle.shots for beat_id in item.covered_beat_ids}
    if covered != {item.beat_id for item in plan.beats}:
        raise ShotBundleViolation("BEAT_COVERAGE", "every directing beat must be covered exactly by source identity")
    legal_options = {item.option_id for item in plan.outcome_previews}
    presented = {option_id for item in bundle.shots for option_id in item.option_ids}
    if presented != legal_options:
        raise ShotBundleViolation("OPTION_COVERAGE", "all and only legal options must be presented")
    for shot in bundle.shots:
        if shot.schema_version != "ShotResponsibility/v1" or shot.framing not in ALLOWED_FRAMING:
            raise ShotBundleViolation("SHOT_POLICY", "invalid shot schema or framing")
        if shot.movement_intent not in ALLOWED_MOVEMENT or not 1 <= shot.min_duration_seconds <= shot.max_duration_seconds <= 15:
            raise ShotBundleViolation("SHOT_POLICY", "invalid movement or duration")
        if not shot.continuity_anchors or plan.scene_anchor_asset_id not in shot.continuity_anchors:
            raise ShotBundleViolation("CONTINUITY_LOSS", "scene continuity anchor is required")
        if not shot.asset_role_references or not shot.responsibility or not shot.dialogue_audio_responsibility:
            raise ShotBundleViolation("SHOT_RESPONSIBILITY", "shot responsibility metadata is incomplete")
    return bundle


def compile_shot_bundle(planner: DirectorBeatPlanner, plan: DirectorBeatPlan,
                        preview: DirectorOutcomePreview | None = None) -> ShotBundle:
    if not isinstance(planner, DirectorBeatPlanner):
        raise ShotBundleViolation("PLANNER_INVALID", "validated DirectorBeatPlanner is required")
    try:
        planner.inspect(plan)
        if preview is not None:
            planner.inspect_option_preview(plan.choice_id, plan.scene_id, preview)
    except ValueError as error:
        raise ShotBundleViolation(getattr(error, "code", "PLAN_INVALID"), str(error)) from error
    option_ids = tuple(item.option_id for item in plan.outcome_previews)
    shots = (
        _shot(plan, 1, "establish_geography", (1,), "wide", "dolly", "establish environmental sound"),
        _shot(plan, 2, "state_dramatic_question", (2,), "medium", "locked", "hold dialogue intelligibility"),
        _shot(plan, 3, "character_intent_and_reaction", (3,), "close", "track", "preserve motivated reaction"),
        _shot(plan, 4, "staging_and_asset_continuity", (4,), "wide", "pan", "preserve spatial sound anchors"),
        _shot(plan, 5, "choice_presentation", (5,), "two_shot", "locked", "present options without preference", option_ids=option_ids),
        _shot(plan, 6, "continuity_bridge_and_exit", (6,), "over_shoulder", "handheld_restrained",
              "carry unresolved tension into authored exit", option_ids=option_ids),
    )
    placeholder = ShotBundle("", "", plan.script_id, plan.script_revision, plan.package_hash,
                             plan.director_brief_compile_hash, plan.graph_hash, plan.bible_hash, plan.plan_hash,
                             plan.style_profile_id, plan.choice_id, plan.scene_id,
                             preview.preview_hash if preview else None, shots)
    digest = _digest(_material(placeholder))
    bundle = replace(placeholder, bundle_id=f"shotbundle_{digest[:24]}", bundle_hash=digest)
    return validate_shot_bundle(bundle, plan)


def inspect_shot_bundle(planner: DirectorBeatPlanner, plan: DirectorBeatPlan,
                        bundle: ShotBundle) -> ShotBundle:
    if not isinstance(bundle, ShotBundle):
        raise ShotBundleViolation("BUNDLE_INVALID", "ShotBundle/v1 is required")
    preview = None
    if bundle.selected_outcome_preview_hash:
        preview = next((item for item in plan.outcome_previews
                        if item.preview_hash == bundle.selected_outcome_preview_hash), None)
        if preview is None:
            raise ShotBundleViolation("PREVIEW_SUBSTITUTION", "outcome preview is absent from source plan")
    validate_shot_bundle(bundle, plan)
    expected = compile_shot_bundle(planner, plan, preview)
    if bundle != expected:
        raise ShotBundleViolation("BUNDLE_SOURCE_SUBSTITUTION", "bundle differs from source-truth compilation")
    return bundle


class ShotBundleCompiler:
    def __init__(self, planner: DirectorBeatPlanner) -> None:
        if not isinstance(planner, DirectorBeatPlanner):
            raise ShotBundleViolation("PLANNER_INVALID", "validated planner is required")
        self._planner = planner

    def list_choices(self) -> tuple[tuple[str, str], ...]:
        return self._planner.list_choices()

    def compile(self, choice_id: str, scene_id: str) -> ShotBundle:
        plan = self._planner.compile(choice_id, scene_id)
        return compile_shot_bundle(self._planner, plan)

    def compile_outcome(self, choice_id: str, scene_id: str, option_id: str) -> ShotBundle:
        plan = self._planner.compile(choice_id, scene_id)
        preview = self._planner.compile_option_preview(choice_id, scene_id, option_id)
        return compile_shot_bundle(self._planner, plan, preview)

    def inspect(self, plan: DirectorBeatPlan, bundle: ShotBundle) -> ShotBundle:
        return inspect_shot_bundle(self._planner, plan, bundle)
