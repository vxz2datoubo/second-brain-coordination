"""Versioned synthetic script packages for the offline interactive-film runtime.

The registry is deliberately immutable and contains only synthetic, public-safe
fixtures.  It resolves scripts from the ledger's initial state so legacy saves
remain replayable without adding unverified metadata into old event chains.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .contracts import ScriptPackage, StoryState


class ScriptRegistryViolation(ValueError):
    """Raised when a script, revision, style, or ledger binding is invalid."""


@dataclass(frozen=True)
class StyleProfile:
    style_profile_id: str
    display_name: str
    rendering_rule: str
    invariant: str

    def to_dict(self) -> dict[str, str]:
        return {
            "style_profile_id": self.style_profile_id,
            "display_name": self.display_name,
            "rendering_rule": self.rendering_rule,
            "invariant": self.invariant,
        }


STYLE_PROFILES: tuple[StyleProfile, ...] = (
    StyleProfile(
        "cinematic_live_action",
        "Cinematic live action",
        "Naturalistic cinematography, practical lighting, and restrained performance detail.",
        "Story facts, adult cast identity, wardrobe, props, injuries, space, and camera responsibility remain unchanged.",
    ),
    StyleProfile(
        "stylized_3d",
        "Stylized 3D",
        "Deliberate three-dimensional shape language and physically coherent animated lighting.",
        "Story facts, adult cast identity, wardrobe, props, injuries, space, and camera responsibility remain unchanged.",
    ),
    StyleProfile(
        "japanese_animation",
        "Japanese animation",
        "Hand-drawn cinematic animation with controlled timing and graphic composition.",
        "Story facts, adult cast identity, wardrobe, props, injuries, space, and camera responsibility remain unchanged.",
    ),
    StyleProfile(
        "ink_wash_animation",
        "Ink-wash animation",
        "Ink diffusion, negative space, and painterly motion while preserving readable actions.",
        "Story facts, adult cast identity, wardrobe, props, injuries, space, and camera responsibility remain unchanged.",
    ),
)
_STYLE_BY_ID = {profile.style_profile_id: profile for profile in STYLE_PROFILES}


def _package(
    script_id: str,
    revision: str,
    initial_state: StoryState,
    graph_revision: str,
    scenes: Iterable[str],
    beats: Iterable[str],
) -> ScriptPackage:
    scene_items = tuple(scenes)
    beat_items = tuple(beats)
    return ScriptPackage(
        script_id=script_id,
        script_revision=revision,
        genre=("adventure", "mystery", "crime", "emotion"),
        content_rating="non_explicit",
        season_catalog=("synthetic-season-01",),
        chapter_catalog=("chapter-01",),
        scene_catalog=scene_items,
        world_bible_ref="synthetic:world-bible:" + script_id,
        character_bible_refs=("synthetic:character:mira:v1", "synthetic:character:player:v1"),
        scene_bible_refs=tuple("synthetic:scene:" + scene + ":v1" for scene in scene_items),
        story_beats=beat_items,
        legal_choices=("listen", "approach", "leave"),
        consequence_rules=("verified_graph_transition_only", "meaningful_state_difference_required"),
        reward_rules=("visible_feedback_or_progress", "recorded_tradeoff_or_risk"),
        ending_rules=("approved_terminal_beat_only",),
        style_profiles=tuple(profile.style_profile_id for profile in STYLE_PROFILES),
        asset_manifest_ref="synthetic:asset-manifest:" + script_id + ":v1",
        source_provenance="synthetic_fixture",
        approval_status="approved_for_runtime",
        initial_state=initial_state,
        graph_revision=graph_revision,
    )


SCRIPT_PACKAGES: tuple[ScriptPackage, ...] = (
    _package(
        "synthetic-legacy-archive",
        "SyntheticLegacyArchive/v1",
        StoryState("synthetic_archive", "arrival", {"mira": 0}),
        "SyntheticArchiveGraph/v1",
        ("synthetic_archive",),
        ("arrival", "echo", "threshold", "courtyard", "resolution"),
    ),
    _package(
        "synthetic-three-scene",
        "SyntheticThreeScene/v1",
        StoryState("archive_gate", "arrival", {"mira": 0}),
        "ArchiveJourneyGraph/v1",
        ("archive_gate", "interior_archive", "dawn_courtyard"),
        ("arrival", "echo", "threshold", "accord", "return"),
    ),
    _package(
        "synthetic-night-signal",
        "SyntheticNightSignal/v1",
        StoryState("station_platform", "platform_arrival", {"mira": 0}),
        "NightSignalGraph/v1",
        ("station_platform", "signal_room", "archive_vault", "control_room", "riverside_dawn"),
        ("platform_arrival", "signal_echo", "console", "vault_index", "relay_pause", "daylight_return"),
    ),
    _package(
        "synthetic-harbor-protocol",
        "SyntheticHarborProtocol/v1",
        StoryState("harbor_observatory", "dock_arrival", {"mira": 0}),
        "HarborProtocolGraph/v1",
        ("harbor_observatory", "beacon_room", "map_archive", "public_forum", "sunrise_pier"),
        ("dock_arrival", "beacon_echo", "lens_console", "chart_crosscheck", "witnessed_record", "daylight_return"),
    ),
)
_SCRIPT_BY_ID = {package.script_id: package for package in SCRIPT_PACKAGES}
_SCRIPT_BY_INITIAL = {
    (package.initial_state.scene_id, package.initial_state.beat_id): package for package in SCRIPT_PACKAGES
}


def validate_script_package(package: ScriptPackage) -> None:
    if package.schema != "ScriptPackage/v1":
        raise ScriptRegistryViolation("script package schema must be ScriptPackage/v1")
    if not package.script_id or not package.script_revision:
        raise ScriptRegistryViolation("script package requires non-empty id and revision")
    if package.content_rating != "non_explicit" or package.approval_status != "approved_for_runtime":
        raise ScriptRegistryViolation("only approved non_explicit script packages may enter the offline runtime")
    if package.source_provenance != "synthetic_fixture":
        raise ScriptRegistryViolation("offline registry accepts synthetic fixtures only")
    if not package.style_profiles or set(package.style_profiles) - set(_STYLE_BY_ID):
        raise ScriptRegistryViolation("script package references an unknown style profile")


def all_script_packages() -> tuple[ScriptPackage, ...]:
    for package in SCRIPT_PACKAGES:
        validate_script_package(package)
    return SCRIPT_PACKAGES


def script_package(script_id: str, script_revision: str | None = None) -> ScriptPackage:
    package = _SCRIPT_BY_ID.get(script_id)
    if package is None:
        raise ScriptRegistryViolation("unknown script_id: " + script_id)
    validate_script_package(package)
    if script_revision is not None and script_revision != package.script_revision:
        raise ScriptRegistryViolation("script_revision does not match the registered script")
    return package


def style_profile(style_profile_id: str, package: ScriptPackage | None = None) -> StyleProfile:
    profile = _STYLE_BY_ID.get(style_profile_id)
    if profile is None:
        raise ScriptRegistryViolation("unknown style_profile_id: " + style_profile_id)
    if package is not None and style_profile_id not in package.style_profiles:
        raise ScriptRegistryViolation("style_profile_id is not approved by this script package")
    return profile


def initial_state_for_script(script_id: str, script_revision: str | None = None) -> StoryState:
    return script_package(script_id, script_revision).initial_state


def script_for_initial_state(state: StoryState) -> ScriptPackage:
    package = _SCRIPT_BY_INITIAL.get((state.scene_id, state.beat_id))
    if package is None:
        raise ScriptRegistryViolation("no registered ScriptPackage/v1 for initial state " + state.scene_id + "/" + state.beat_id)
    return script_package(package.script_id, package.script_revision)


def script_for_ledger(ledger: Any) -> ScriptPackage:
    ledger.verify_chain()
    if not ledger.events or ledger.events[0].event_type != "story_initialized":
        raise ScriptRegistryViolation("story ledger must begin with story_initialized")
    initial = StoryState.from_dict(ledger.events[0].payload["state"])
    package = script_for_initial_state(initial)
    from .continuity import graph_for_ledger

    graph = graph_for_ledger(ledger)
    if graph.revision != package.graph_revision:
        raise ScriptRegistryViolation("registered script graph revision does not match the immutable ledger route")
    return package


def script_catalog() -> dict[str, Any]:
    return {
        "schema": "ScriptPackageCatalog/v1",
        "status": "synthetic_registry_verified",
        "script_count": len(all_script_packages()),
        "style_profiles": [profile.to_dict() for profile in STYLE_PROFILES],
        "scripts": [package.to_dict() for package in all_script_packages()],
        "boundary": {
            "provenance": "synthetic_fixture_only",
            "external_or_private_assets_loaded": False,
            "eustia_imported": False,
        },
    }
