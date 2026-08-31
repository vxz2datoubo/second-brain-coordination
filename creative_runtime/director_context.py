"""Explicit multi-script binding for the legacy-compatible director compiler."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from .contracts import DirectorBriefV2, canonical_json
from .director import VerifiedDirectorCompilation, compile_verified_director
from .script_packages import ScriptRegistryViolation, script_for_ledger, script_package, style_profile


class DirectorContextViolation(ValueError):
    """Raised before a director receives a mismatched script/campaign context."""


DIRECTOR_POLICY_REVISION = "OfflineDirectorPolicy/v2"


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def campaign_id_for_ledger(ledger: Any) -> str:
    ledger.verify_chain()
    if not ledger.events:
        raise DirectorContextViolation("campaign binding requires a non-empty ledger")
    return "camp_" + ledger.events[0].event_hash[:20]


@dataclass(frozen=True)
class DirectorContextCompilation:
    brief_v2: DirectorBriefV2
    legacy_compilation: VerifiedDirectorCompilation
    rendering_profile: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "director_v2_verified",
            "brief": self.brief_v2.to_dict(),
            "rendering_profile": self.rendering_profile,
            "legacy_verified_input": self.legacy_compilation.verified_input.to_dict(),
            "shots": [shot.to_dict() for shot in self.legacy_compilation.compilation.shots],
            "quality_report": self.legacy_compilation.compilation.quality_report.to_dict(),
        }


def compile_verified_director_v2(
    ledger: Any,
    *,
    script_id: str,
    script_revision: str,
    style_profile_id: str,
    campaign_id: str | None = None,
    director_policy_revision: str = DIRECTOR_POLICY_REVISION,
) -> DirectorContextCompilation:
    """Compile a director context only when all explicit bindings agree.

    The existing director compiler remains untouched for old commands.  This
    additive v2 entry point makes multi-script identity mandatory for every new
    consumer, while the ledger's immutable initial event keeps old saves valid.
    """

    try:
        expected_package = script_for_ledger(ledger)
        requested_package = script_package(script_id, script_revision)
        profile = style_profile(style_profile_id, requested_package)
    except ScriptRegistryViolation as error:
        raise DirectorContextViolation(str(error)) from error
    if requested_package != expected_package:
        raise DirectorContextViolation("requested script does not match the immutable campaign script binding")
    if director_policy_revision != DIRECTOR_POLICY_REVISION:
        raise DirectorContextViolation("unregistered director_policy_revision")
    resolved_campaign_id = campaign_id_for_ledger(ledger)
    if campaign_id is not None and campaign_id != resolved_campaign_id:
        raise DirectorContextViolation("campaign_id does not match this immutable campaign ledger")

    legacy = compile_verified_director(ledger)
    verified = legacy.verified_input
    state_hash = _hash(verified.state.to_dict())
    scene_ref = "art_scene_" + verified.state.scene_id
    brief = DirectorBriefV2(
        script_id=requested_package.script_id,
        script_revision=requested_package.script_revision,
        campaign_id=resolved_campaign_id,
        verified_story_state_hash=state_hash,
        style_profile_id=profile.style_profile_id,
        cast_revision_ids=("cast_mira_synthetic_v1", "cast_player_synthetic_v1"),
        scene_asset_refs=(scene_ref,),
        continuity_ledger_hash=verified.timeline_hash,
        director_policy_revision=director_policy_revision,
        narrative_brief=legacy.compilation.brief,
    )
    validate_director_brief_v2(brief, ledger, legacy)
    return DirectorContextCompilation(brief, legacy, profile.rendering_rule)


def validate_director_brief_v2(brief: DirectorBriefV2, ledger: Any, legacy: VerifiedDirectorCompilation) -> None:
    """Fail closed if a context binding differs from its verified source."""

    if brief.schema != "DirectorBrief/v2":
        raise DirectorContextViolation("unexpected director brief schema")
    try:
        package = script_for_ledger(ledger)
        requested = script_package(brief.script_id, brief.script_revision)
        style_profile(brief.style_profile_id, requested)
    except ScriptRegistryViolation as error:
        raise DirectorContextViolation(str(error)) from error
    if package != requested:
        raise DirectorContextViolation("brief script binding is inconsistent with immutable ledger initialization")
    if brief.campaign_id != campaign_id_for_ledger(ledger):
        raise DirectorContextViolation("brief campaign_id is inconsistent with immutable ledger initialization")
    if brief.verified_story_state_hash != _hash(legacy.verified_input.state.to_dict()):
        raise DirectorContextViolation("brief verified_story_state_hash does not match verified state")
    if brief.continuity_ledger_hash != legacy.verified_input.timeline_hash:
        raise DirectorContextViolation("brief continuity_ledger_hash does not match verified timeline")
    if brief.narrative_brief != legacy.compilation.brief:
        raise DirectorContextViolation("brief narrative source differs from the director's verified compilation")
    expected_scene_ref = "art_scene_" + legacy.verified_input.state.scene_id
    if brief.scene_asset_refs != (expected_scene_ref,):
        raise DirectorContextViolation("brief scene_asset_refs must bind only the current verified scene")
    if brief.cast_revision_ids != ("cast_mira_synthetic_v1", "cast_player_synthetic_v1"):
        raise DirectorContextViolation("brief cast revisions are not the approved synthetic cast anchors")
    if brief.director_policy_revision != DIRECTOR_POLICY_REVISION:
        raise DirectorContextViolation("brief director policy is not registered")
    if not legacy.compilation.quality_report.can_generate:
        raise DirectorContextViolation("director quality gate blocked the underlying verified compilation")
