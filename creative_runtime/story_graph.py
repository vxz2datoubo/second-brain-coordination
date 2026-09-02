"""Immutable authored story graph and static consequence coverage."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from .contracts import ScriptPackage, canonical_json


ALLOWED_CHANGE_DIMENSIONS = frozenset(
    {"clue", "relationship", "resource", "risk", "quest", "scene", "ending"}
)


class StoryGraphViolation(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class StaticConsequence:
    summary: str
    changes: tuple[str, ...]
    reward_tags: tuple[str, ...]
    cost_tags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "changes": list(self.changes),
            "reward_tags": list(self.reward_tags),
            "cost_tags": list(self.cost_tags),
        }


@dataclass(frozen=True)
class ChoiceOption:
    option_id: str
    label: str
    consequence: StaticConsequence
    next_choice_id: str | None = None
    ending_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "label": self.label,
            "consequence": self.consequence.to_dict(),
            "next_choice_id": self.next_choice_id,
            "ending_id": self.ending_id,
        }


@dataclass(frozen=True)
class MajorChoicePoint:
    choice_id: str
    act_id: str
    chapter_id: str
    scene_id: str
    order: int
    dramatic_question: str
    options: tuple[ChoiceOption, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "choice_id": self.choice_id,
            "act_id": self.act_id,
            "chapter_id": self.chapter_id,
            "scene_id": self.scene_id,
            "order": self.order,
            "dramatic_question": self.dramatic_question,
            "options": [item.to_dict() for item in self.options],
        }


@dataclass(frozen=True)
class StoryChapter:
    chapter_id: str
    act_id: str
    order: int
    title: str
    choice_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "act_id": self.act_id,
            "order": self.order,
            "title": self.title,
            "choice_ids": list(self.choice_ids),
        }


@dataclass(frozen=True)
class StoryAct:
    act_id: str
    order: int
    title: str
    chapter_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "act_id": self.act_id,
            "order": self.order,
            "title": self.title,
            "chapter_ids": list(self.chapter_ids),
        }


@dataclass(frozen=True)
class ImmutableStoryGraph:
    script_id: str
    script_revision: str
    package_hash: str
    entry_choice_id: str
    acts: tuple[StoryAct, ...]
    chapters: tuple[StoryChapter, ...]
    choices: tuple[MajorChoicePoint, ...]
    ending_ids: tuple[str, ...]
    schema_version: str = "StaticStoryGraph/v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "script_id": self.script_id,
            "script_revision": self.script_revision,
            "package_hash": self.package_hash,
            "entry_choice_id": self.entry_choice_id,
            "acts": [item.to_dict() for item in self.acts],
            "chapters": [item.to_dict() for item in self.chapters],
            "choices": [item.to_dict() for item in self.choices],
            "ending_ids": list(self.ending_ids),
        }

    @property
    def graph_hash(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConsequenceCoverage:
    graph_hash: str
    option_count: int
    dimension_counts: Mapping[str, int]
    option_hashes: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension_counts", MappingProxyType(dict(self.dimension_counts)))
        object.__setattr__(self, "option_hashes", MappingProxyType(dict(self.option_hashes)))


def validate_story_graph(graph: ImmutableStoryGraph) -> ImmutableStoryGraph:
    if graph.schema_version != "StaticStoryGraph/v1":
        raise StoryGraphViolation("GRAPH_SCHEMA", "unsupported graph schema")
    if len(graph.acts) != 3 or [item.order for item in graph.acts] != [1, 2, 3]:
        raise StoryGraphViolation("ACT_STRUCTURE", "flagship graph requires exactly ordered 3 acts")
    if len(graph.chapters) != 6 or [item.order for item in graph.chapters] != list(range(1, 7)):
        raise StoryGraphViolation("CHAPTER_STRUCTURE", "flagship graph requires exactly ordered 6 chapters")
    if len(graph.choices) != 12 or [item.order for item in graph.choices] != list(range(1, 13)):
        raise StoryGraphViolation("CHOICE_STRUCTURE", "flagship graph requires exactly ordered 12 choices")

    act_ids = [item.act_id for item in graph.acts]
    chapter_ids = [item.chapter_id for item in graph.chapters]
    choice_ids = [item.choice_id for item in graph.choices]
    if len(set(act_ids)) != 3 or len(set(chapter_ids)) != 6 or len(set(choice_ids)) != 12:
        raise StoryGraphViolation("DUPLICATE_ID", "act, chapter and choice IDs must be unique")
    if graph.entry_choice_id != graph.choices[0].choice_id:
        raise StoryGraphViolation("ENTRY_INVALID", "entry must be the first authored major choice")
    if len(set(graph.ending_ids)) != len(graph.ending_ids) or not graph.ending_ids:
        raise StoryGraphViolation("ENDING_INVALID", "ending IDs must be present and unique")

    chapter_by_id = {item.chapter_id: item for item in graph.chapters}
    choice_by_id = {item.choice_id: item for item in graph.choices}
    choice_order = {item.choice_id: item.order for item in graph.choices}
    if tuple(chapter_id for act in graph.acts for chapter_id in act.chapter_ids) != tuple(chapter_ids):
        raise StoryGraphViolation("ACT_CHAPTER_REFERENCE", "acts must own all chapters exactly once in order")
    for chapter in graph.chapters:
        if chapter.act_id not in act_ids:
            raise StoryGraphViolation("CHAPTER_ACT_REFERENCE", "chapter references unknown act")
        act = next(item for item in graph.acts if item.act_id == chapter.act_id)
        if chapter.chapter_id not in act.chapter_ids or len(chapter.choice_ids) != 2:
            raise StoryGraphViolation("CHAPTER_CHOICE_REFERENCE", "each chapter must own exactly two choices")
    if tuple(choice_id for chapter in graph.chapters for choice_id in chapter.choice_ids) != tuple(choice_ids):
        raise StoryGraphViolation("CHAPTER_CHOICE_REFERENCE", "chapters must own all choices exactly once in order")

    reachable = {graph.entry_choice_id}
    frontier = [graph.entry_choice_id]
    option_ids: set[str] = set()
    while frontier:
        current_id = frontier.pop()
        current = choice_by_id[current_id]
        if current.chapter_id not in chapter_by_id or current.act_id != chapter_by_id[current.chapter_id].act_id:
            raise StoryGraphViolation("CHOICE_PARENT_REFERENCE", "choice has inconsistent act or chapter")
        if not 2 <= len(current.options) <= 4:
            raise StoryGraphViolation("OPTION_COUNT", "each major choice needs 2-4 authored options")
        for option in current.options:
            if not option.option_id or option.option_id in option_ids:
                raise StoryGraphViolation("OPTION_ID", "option IDs must be present and globally unique")
            option_ids.add(option.option_id)
            if not option.consequence.summary or not option.consequence.changes:
                raise StoryGraphViolation("CONSEQUENCE_MISSING", "every option requires a visible static consequence")
            if not set(option.consequence.changes).issubset(ALLOWED_CHANGE_DIMENSIONS):
                raise StoryGraphViolation("CONSEQUENCE_DIMENSION", "consequence uses an unknown change dimension")
            if bool(option.next_choice_id) == bool(option.ending_id):
                raise StoryGraphViolation("EDGE_TARGET", "option requires exactly one next choice or ending")
            if option.next_choice_id:
                if option.next_choice_id not in choice_by_id:
                    raise StoryGraphViolation("DANGLING_EDGE", "option targets an unknown choice")
                if choice_order[option.next_choice_id] != current.order + 1:
                    raise StoryGraphViolation("ILLEGAL_JUMP_OR_CYCLE", "static graph edges must advance one choice")
                if option.next_choice_id not in reachable:
                    reachable.add(option.next_choice_id)
                    frontier.append(option.next_choice_id)
            elif option.ending_id not in graph.ending_ids:
                raise StoryGraphViolation("DANGLING_ENDING", "option targets an unknown ending")
        if current.order < 12 and any(option.ending_id for option in current.options):
            raise StoryGraphViolation("EARLY_ENDING", "only the final major choice may resolve an ending")
        if current.order == 12 and any(option.next_choice_id for option in current.options):
            raise StoryGraphViolation("FINAL_CONTINUES", "final major choice must resolve endings")
    if reachable != set(choice_ids):
        raise StoryGraphViolation("UNREACHABLE_CHOICE", "all authored choices must be reachable")
    return graph


def validate_graph_for_package(graph: ImmutableStoryGraph, package: ScriptPackage) -> ImmutableStoryGraph:
    validate_story_graph(graph)
    if (graph.script_id, graph.script_revision, graph.package_hash) != (
        package.script_id,
        package.script_revision,
        package.package_hash,
    ):
        raise StoryGraphViolation("CROSS_SCRIPT_IDENTITY", "graph and ScriptPackage identity differ")
    package_beats = {str(item.get("beat_id", "")) for item in package.story_beats}
    if package_beats != {item.choice_id for item in graph.choices}:
        raise StoryGraphViolation("PACKAGE_BEAT_REFERENCE", "package beats do not exactly match graph choices")
    for choice in graph.choices:
        if set(package.legal_choices.get(choice.choice_id, ())) != {item.option_id for item in choice.options}:
            raise StoryGraphViolation("PACKAGE_OPTION_REFERENCE", "package legal choices differ from graph options")
    return graph


def compile_consequence_coverage(graph: ImmutableStoryGraph) -> ConsequenceCoverage:
    validate_story_graph(graph)
    dimensions = {item: 0 for item in sorted(ALLOWED_CHANGE_DIMENSIONS)}
    option_hashes: dict[str, str] = {}
    for choice in graph.choices:
        for option in choice.options:
            for dimension in option.consequence.changes:
                dimensions[dimension] += 1
            option_hashes[option.option_id] = hashlib.sha256(
                canonical_json(option.to_dict()).encode("utf-8")
            ).hexdigest()
    return ConsequenceCoverage(
        graph_hash=graph.graph_hash,
        option_count=len(option_hashes),
        dimension_counts=dimensions,
        option_hashes=option_hashes,
    )
