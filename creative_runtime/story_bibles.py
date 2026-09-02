"""Immutable character and scene bibles bound to one approved story graph."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from .contracts import ScriptPackage, canonical_json
from .story_graph import ImmutableStoryGraph, validate_graph_for_package


class StoryBibleViolation(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class CharacterBible:
    character_id: str
    display_name: str
    age: int
    role: str
    motivation: str
    goal: str
    values: tuple[str, ...]
    fears: tuple[str, ...]
    knowledge_constraints: tuple[str, ...]
    appearance_anchor_asset_id: str
    arc_choice_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "display_name": self.display_name,
            "age": self.age,
            "role": self.role,
            "motivation": self.motivation,
            "goal": self.goal,
            "values": list(self.values),
            "fears": list(self.fears),
            "knowledge_constraints": list(self.knowledge_constraints),
            "appearance_anchor_asset_id": self.appearance_anchor_asset_id,
            "arc_choice_ids": list(self.arc_choice_ids),
        }


@dataclass(frozen=True)
class SceneBible:
    scene_id: str
    display_name: str
    location: str
    time_window: str
    spatial_anchor: str
    staging_constraints: tuple[str, ...]
    scene_anchor_asset_id: str
    allowed_choice_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "display_name": self.display_name,
            "location": self.location,
            "time_window": self.time_window,
            "spatial_anchor": self.spatial_anchor,
            "staging_constraints": list(self.staging_constraints),
            "scene_anchor_asset_id": self.scene_anchor_asset_id,
            "allowed_choice_ids": list(self.allowed_choice_ids),
        }


@dataclass(frozen=True)
class StoryBibleBundle:
    script_id: str
    script_revision: str
    package_hash: str
    graph_hash: str
    characters: tuple[CharacterBible, ...]
    scenes: tuple[SceneBible, ...]
    schema_version: str = "StoryBibleBundle/v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "script_id": self.script_id,
            "script_revision": self.script_revision,
            "package_hash": self.package_hash,
            "graph_hash": self.graph_hash,
            "characters": [item.to_dict() for item in self.characters],
            "scenes": [item.to_dict() for item in self.scenes],
        }

    @property
    def bible_hash(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()


def _require_text(code: str, *values: str) -> None:
    if any(not str(value).strip() for value in values):
        raise StoryBibleViolation(code, "required authored text is missing")


def validate_story_bibles(
    bundle: StoryBibleBundle,
    graph: ImmutableStoryGraph,
    package: ScriptPackage,
) -> StoryBibleBundle:
    try:
        validate_graph_for_package(graph, package)
    except ValueError as error:
        raise StoryBibleViolation("GRAPH_PACKAGE_INVALID", str(error)) from error
    if bundle.schema_version != "StoryBibleBundle/v1":
        raise StoryBibleViolation("BIBLE_SCHEMA", "unsupported bible schema")
    identity = (package.script_id, package.script_revision, package.package_hash, graph.graph_hash)
    if (bundle.script_id, bundle.script_revision, bundle.package_hash, bundle.graph_hash) != identity:
        raise StoryBibleViolation("CROSS_SCRIPT_IDENTITY", "bibles, graph and package identity differ")

    character_ids = [item.character_id for item in bundle.characters]
    scene_ids = [item.scene_id for item in bundle.scenes]
    if not character_ids or len(character_ids) != len(set(character_ids)):
        raise StoryBibleViolation("CHARACTER_ID", "character IDs must be present and unique")
    if not scene_ids or len(scene_ids) != len(set(scene_ids)):
        raise StoryBibleViolation("SCENE_ID", "scene IDs must be present and unique")
    graph_choice_ids = {item.choice_id for item in graph.choices}
    graph_scene_ids = {item.scene_id for item in graph.choices}
    if set(scene_ids) != graph_scene_ids:
        raise StoryBibleViolation("SCENE_COVERAGE", "scene bibles must exactly cover graph scenes")

    assets = {str(item.get("asset_id", "")): str(item.get("role", "")) for item in package.asset_manifest}
    for character in bundle.characters:
        _require_text(
            "CHARACTER_FIELD",
            character.character_id,
            character.display_name,
            character.role,
            character.motivation,
            character.goal,
        )
        if character.age < 18:
            raise StoryBibleViolation("CHARACTER_NOT_ADULT", "all principal characters must be adults")
        if not character.values or not character.fears or not character.knowledge_constraints:
            raise StoryBibleViolation("CHARACTER_DEPTH", "values, fears and knowledge constraints are required")
        if not character.arc_choice_ids or not set(character.arc_choice_ids).issubset(graph_choice_ids):
            raise StoryBibleViolation("CHARACTER_ARC_REFERENCE", "character arc references unknown choices")
        if assets.get(character.appearance_anchor_asset_id) != "character_anchor":
            raise StoryBibleViolation("CHARACTER_ASSET_REFERENCE", "character anchor is missing or has wrong role")

    choices_by_scene: dict[str, list[str]] = {scene_id: [] for scene_id in graph_scene_ids}
    for choice in graph.choices:
        choices_by_scene[choice.scene_id].append(choice.choice_id)
    for scene in bundle.scenes:
        _require_text(
            "SCENE_FIELD",
            scene.scene_id,
            scene.display_name,
            scene.location,
            scene.time_window,
            scene.spatial_anchor,
        )
        if not scene.staging_constraints:
            raise StoryBibleViolation("SCENE_STAGING", "each scene needs staging constraints")
        if tuple(choices_by_scene[scene.scene_id]) != scene.allowed_choice_ids:
            raise StoryBibleViolation("SCENE_CHOICE_REFERENCE", "scene choices differ from graph truth")
        if assets.get(scene.scene_anchor_asset_id) != "scene_anchor":
            raise StoryBibleViolation("SCENE_ASSET_REFERENCE", "scene anchor is missing or has wrong role")
    return bundle
