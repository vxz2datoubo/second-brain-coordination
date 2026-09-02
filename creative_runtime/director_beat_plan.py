"""Pure DirectorBeatPlan/v1 compiler over validated immutable content."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from typing import Any

from .contracts import DirectorBriefV2CompiledContent, ScriptPackage, canonical_json
from .director_v2 import inspect_director_brief_v2
from .script_catalog import PersistentScriptCatalog, ScriptCatalogViolation
from .story_bibles import StoryBibleBundle, validate_story_bibles
from .story_graph import ChoiceOption, ImmutableStoryGraph, MajorChoicePoint, validate_graph_for_package


STYLE_PRESENTATION = {
    "cinematic_live_action": ("restrained live-action blocking", "motivated practical light", "diegetic tension"),
    "stylized_3d": ("expressive authored 3D blocking", "sculpted volumetric light", "spatial cinematic mix"),
    "japanese_animation": ("graphic anime staging", "controlled color-key lighting", "dramatic animation mix"),
    "ink_animation": ("ink-wash negative-space staging", "tonal wash and silhouette", "minimal acoustic score"),
}


class DirectorBeatPlanViolation(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DirectorBeat:
    beat_id: str
    order: int
    beat_type: str
    objective: str
    constraints: tuple[str, ...]
    presentation_intent: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "order": self.order,
            "beat_type": self.beat_type,
            "objective": self.objective,
            "constraints": list(self.constraints),
            "presentation_intent": self.presentation_intent,
        }


@dataclass(frozen=True)
class DirectorOutcomePreview:
    option_id: str
    option_label: str
    consequence_summary: str
    change_dimensions: tuple[str, ...]
    reward_tags: tuple[str, ...]
    cost_tags: tuple[str, ...]
    next_choice_id: str | None
    ending_id: str | None
    exit_intent: str
    preview_hash: str
    schema_version: str = "DirectorOutcomePreview/v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "option_id": self.option_id,
            "option_label": self.option_label,
            "consequence_summary": self.consequence_summary,
            "change_dimensions": list(self.change_dimensions),
            "reward_tags": list(self.reward_tags),
            "cost_tags": list(self.cost_tags),
            "next_choice_id": self.next_choice_id,
            "ending_id": self.ending_id,
            "exit_intent": self.exit_intent,
            "preview_hash": self.preview_hash,
        }


@dataclass(frozen=True)
class DirectorBeatPlan:
    plan_id: str
    plan_hash: str
    script_id: str
    script_revision: str
    package_hash: str
    director_brief_compile_hash: str
    graph_hash: str
    bible_hash: str
    style_profile_id: str
    choice_id: str
    scene_id: str
    scene_anchor_asset_id: str
    character_anchor_asset_ids: tuple[str, ...]
    dramatic_question: str
    beats: tuple[DirectorBeat, ...]
    outcome_previews: tuple[DirectorOutcomePreview, ...]
    schema_version: str = "DirectorBeatPlan/v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "script_id": self.script_id,
            "script_revision": self.script_revision,
            "package_hash": self.package_hash,
            "director_brief_compile_hash": self.director_brief_compile_hash,
            "graph_hash": self.graph_hash,
            "bible_hash": self.bible_hash,
            "style_profile_id": self.style_profile_id,
            "choice_id": self.choice_id,
            "scene_id": self.scene_id,
            "scene_anchor_asset_id": self.scene_anchor_asset_id,
            "character_anchor_asset_ids": list(self.character_anchor_asset_ids),
            "dramatic_question": self.dramatic_question,
            "beats": [item.to_dict() for item in self.beats],
            "outcome_previews": [item.to_dict() for item in self.outcome_previews],
        }


def _without_hashes(value: DirectorBeatPlan) -> dict[str, Any]:
    material = value.to_dict()
    material.pop("plan_id", None)
    material.pop("plan_hash", None)
    return material


def _preview(option: ChoiceOption) -> DirectorOutcomePreview:
    exit_intent = (
        f"preserve continuity into authored choice {option.next_choice_id}"
        if option.next_choice_id
        else f"resolve visual and emotional continuity into ending {option.ending_id}"
    )
    placeholder = DirectorOutcomePreview(
        option.option_id,
        option.label,
        option.consequence.summary,
        option.consequence.changes,
        option.consequence.reward_tags,
        option.consequence.cost_tags,
        option.next_choice_id,
        option.ending_id,
        exit_intent,
        "",
    )
    material = placeholder.to_dict()
    material.pop("preview_hash")
    return replace(placeholder, preview_hash=_digest(material))


def _source_truth(
    catalog: PersistentScriptCatalog,
    brief: DirectorBriefV2CompiledContent,
    graph: ImmutableStoryGraph,
    bibles: StoryBibleBundle,
) -> ScriptPackage:
    if not isinstance(catalog, PersistentScriptCatalog):
        raise DirectorBeatPlanViolation("CATALOG_INVALID", "validated persistent catalog is required")
    if not isinstance(graph, ImmutableStoryGraph):
        raise DirectorBeatPlanViolation("GRAPH_INVALID", "StaticStoryGraph/v1 is required")
    if not isinstance(bibles, StoryBibleBundle):
        raise DirectorBeatPlanViolation("BIBLES_INVALID", "StoryBibleBundle/v1 is required")
    try:
        inspected = inspect_director_brief_v2(catalog, brief)
        package = catalog.consume_director_binding(inspected.content_binding)
        validate_graph_for_package(graph, package)
        validate_story_bibles(bibles, graph, package)
    except (ValueError, ScriptCatalogViolation) as error:
        raise DirectorBeatPlanViolation(getattr(error, "code", "SOURCE_TRUTH_INVALID"), str(error)) from error
    if inspected.style_profile.style_profile_id not in STYLE_PRESENTATION:
        raise DirectorBeatPlanViolation("STYLE_UNSUPPORTED", "style has no approved presentation policy")
    return package


def _choice_and_scene(
    graph: ImmutableStoryGraph,
    bibles: StoryBibleBundle,
    choice_id: str,
    scene_id: str,
):
    choice = next((item for item in graph.choices if item.choice_id == choice_id), None)
    if choice is None:
        raise DirectorBeatPlanViolation("CHOICE_UNKNOWN", "choice is absent from source graph")
    if choice.scene_id != scene_id:
        raise DirectorBeatPlanViolation("SCENE_OWNERSHIP", "choice does not belong to requested scene")
    scene = next((item for item in bibles.scenes if item.scene_id == scene_id), None)
    if scene is None or choice_id not in scene.allowed_choice_ids:
        raise DirectorBeatPlanViolation("SCENE_CONTINUITY", "scene bible does not authorize this choice")
    return choice, scene


def compile_director_beat_plan(
    catalog: PersistentScriptCatalog,
    brief: DirectorBriefV2CompiledContent,
    graph: ImmutableStoryGraph,
    bibles: StoryBibleBundle,
    *,
    choice_id: str,
    scene_id: str,
) -> DirectorBeatPlan:
    """Compile one explicit content address; no player choice is recorded."""

    _source_truth(catalog, brief, graph, bibles)
    choice, scene = _choice_and_scene(graph, bibles, choice_id, scene_id)
    style = STYLE_PRESENTATION[brief.style_profile.style_profile_id]
    knowledge = tuple(
        f"{item.character_id}: {constraint}"
        for item in bibles.characters
        for constraint in item.knowledge_constraints
    )
    anchors = tuple(item.appearance_anchor_asset_id for item in bibles.characters)
    previews = tuple(_preview(option) for option in choice.options)
    option_constraints = tuple(
        f"{item.option_id}: {item.consequence.summary}; reward={','.join(item.consequence.reward_tags)}; cost={','.join(item.consequence.cost_tags)}"
        for item in choice.options
    )
    beats = (
        DirectorBeat(f"{choice_id}:01", 1, "pre_choice_setup", f"establish {scene.display_name} and decision pressure",
                     (scene.spatial_anchor, scene.time_window, *scene.staging_constraints), style[0]),
        DirectorBeat(f"{choice_id}:02", 2, "dramatic_question", choice.dramatic_question,
                     ("do not imply that the player already selected an option",), "hold a readable decision frame"),
        DirectorBeat(f"{choice_id}:03", 3, "character_continuity", "preserve adult character identity, motive and knowledge",
                     knowledge, "prioritize motivated reaction over exposition"),
        DirectorBeat(f"{choice_id}:04", 4, "scene_staging", "maintain spatial and asset continuity",
                     (scene.scene_anchor_asset_id, *anchors, *scene.staging_constraints), style[1]),
        DirectorBeat(f"{choice_id}:05", 5, "option_presentation", "present every authored legal option without preference",
                     option_constraints, style[2]),
        DirectorBeat(f"{choice_id}:06", 6, "continuity_safe_exit", "prepare authored exits without mutating story state",
                     tuple(item.exit_intent for item in previews), "end on unresolved player agency"),
    )
    placeholder = DirectorBeatPlan(
        "", "", brief.content_binding.script_id, brief.content_binding.script_revision,
        brief.content_binding.package_hash, brief.compile_hash, graph.graph_hash, bibles.bible_hash,
        brief.style_profile.style_profile_id, choice.choice_id, scene.scene_id,
        scene.scene_anchor_asset_id, anchors, choice.dramatic_question, beats, previews,
    )
    plan_hash = _digest(_without_hashes(placeholder))
    return replace(placeholder, plan_id=f"directorbeat_{plan_hash[:24]}", plan_hash=plan_hash)


def inspect_director_beat_plan(
    catalog: PersistentScriptCatalog,
    brief: DirectorBriefV2CompiledContent,
    graph: ImmutableStoryGraph,
    bibles: StoryBibleBundle,
    plan: DirectorBeatPlan,
) -> DirectorBeatPlan:
    if not isinstance(plan, DirectorBeatPlan):
        raise DirectorBeatPlanViolation("PLAN_INVALID", "DirectorBeatPlan/v1 is required")
    if plan.schema_version != "DirectorBeatPlan/v1":
        raise DirectorBeatPlanViolation("PLAN_SCHEMA", "unsupported plan schema")
    if plan.plan_hash != _digest(_without_hashes(plan)) or plan.plan_id != f"directorbeat_{plan.plan_hash[:24]}":
        raise DirectorBeatPlanViolation("PLAN_HASH_MISMATCH", "plan hash or ID is stale or tampered")
    expected = compile_director_beat_plan(
        catalog, brief, graph, bibles, choice_id=plan.choice_id, scene_id=plan.scene_id
    )
    if expected != plan:
        raise DirectorBeatPlanViolation("PLAN_SOURCE_SUBSTITUTION", "plan differs from freshly compiled source truth")
    return plan


class DirectorBeatPlanner:
    """Read-only facade; selectors address authored content, never player state."""

    def __init__(self, catalog: PersistentScriptCatalog, brief: DirectorBriefV2CompiledContent,
                 graph: ImmutableStoryGraph, bibles: StoryBibleBundle) -> None:
        _source_truth(catalog, brief, graph, bibles)
        self._catalog, self._brief, self._graph, self._bibles = catalog, brief, graph, bibles

    def list_choices(self) -> tuple[tuple[str, str], ...]:
        _source_truth(self._catalog, self._brief, self._graph, self._bibles)
        return tuple((item.choice_id, item.scene_id) for item in self._graph.choices)

    def compile(self, choice_id: str, scene_id: str) -> DirectorBeatPlan:
        return compile_director_beat_plan(self._catalog, self._brief, self._graph, self._bibles,
                                          choice_id=choice_id, scene_id=scene_id)

    def inspect(self, plan: DirectorBeatPlan) -> DirectorBeatPlan:
        return inspect_director_beat_plan(self._catalog, self._brief, self._graph, self._bibles, plan)

    def compile_option_preview(self, choice_id: str, scene_id: str, option_id: str) -> DirectorOutcomePreview:
        plan = self.compile(choice_id, scene_id)
        preview = next((item for item in plan.outcome_previews if item.option_id == option_id), None)
        if preview is None:
            raise DirectorBeatPlanViolation("OPTION_UNKNOWN", "option is absent from authored choice")
        return preview

    def inspect_option_preview(self, choice_id: str, scene_id: str,
                               preview: DirectorOutcomePreview) -> DirectorOutcomePreview:
        if not isinstance(preview, DirectorOutcomePreview) or preview.schema_version != "DirectorOutcomePreview/v1":
            raise DirectorBeatPlanViolation("PREVIEW_INVALID", "DirectorOutcomePreview/v1 is required")
        expected = self.compile_option_preview(choice_id, scene_id, preview.option_id)
        if preview != expected:
            raise DirectorBeatPlanViolation("PREVIEW_SOURCE_SUBSTITUTION", "preview differs from source truth")
        return preview
