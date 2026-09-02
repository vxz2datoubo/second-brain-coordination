"""Two approved, entirely synthetic ScriptPackage/v1 fixtures."""

from __future__ import annotations

from .contracts import ScriptPackage
from .script_registry import build_script_package, style_profiles_v1


def _archive_case() -> ScriptPackage:
    return build_script_package(
        script_id="synthetic_archive_case",
        script_revision="1.0.0",
        genre=("mystery", "adventure", "emotional"),
        content_rating="non_explicit",
        world_bible={
            "title": "回声档案馆",
            "premise": "Two adult investigators trace a falsified evacuation record before dawn.",
            "immutable_facts": ("the archive is sealed at midnight", "Mira is an adult investigator"),
        },
        character_bibles=(
            {"character_id": "mira", "adult": True, "goal": "protect the witness", "secret": "heard the alarm early"},
            {"character_id": "ren", "adult": True, "goal": "recover the authentic ledger", "secret": "knows the old cipher"},
        ),
        scene_bibles=(
            {"scene_id": "archive_gate", "spatial_anchor": "iron gate faces the east stair"},
            {"scene_id": "interior_archive", "spatial_anchor": "reading table remains north of the vault"},
        ),
        story_beats=(
            {"beat_id": "arrival", "scene_id": "archive_gate", "purpose": "establish warning and trust"},
            {"beat_id": "threshold", "scene_id": "interior_archive", "purpose": "commit to a costly search"},
        ),
        legal_choices={"arrival": ("listen", "approach"), "threshold": ("promise", "retreat")},
        consequence_rules={
            "listen": {"known_fact_add": "a witness is inside", "risk_delta": 1},
            "approach": {"relationship_delta": {"mira": 1}},
            "promise": {"relationship_delta": {"mira": 1}, "risk_delta": -1},
            "retreat": {"flag_set": {"meeting": "deferred"}},
        },
        reward_rules={"meaningful_feedback": ("clue", "ally_reaction", "route_unlock")},
        ending_rules={"accord": {"requires": ("promise",)}, "courtyard": {"requires": ("retreat",)}},
        style_profiles=style_profiles_v1(),
        asset_manifest=(
            {"asset_id": "synthetic_character_mira_v1", "role": "character_anchor", "synthetic": True},
            {"asset_id": "synthetic_archive_gate_v1", "role": "scene_anchor", "synthetic": True},
        ),
        source_provenance={
            "source_id": "r176_synthetic_fixture_archive",
            "classification": "SYNTHETIC",
            "approved_for_reuse": True,
            "approval_record": "ISSUE-534-R176",
        },
        approval_status="approved",
    )


def _tideglass_signal() -> ScriptPackage:
    return build_script_package(
        script_id="synthetic_tideglass_signal",
        script_revision="1.0.0",
        genre=("adventure", "crime", "mystery", "emotional"),
        content_rating="non_explicit",
        world_bible={
            "title": "潮镜信号",
            "premise": "An adult salvage crew must expose a staged lighthouse failure before the tide turns.",
            "immutable_facts": ("the beacon has two power circuits", "all principal characters are adults"),
        },
        character_bibles=(
            {"character_id": "lin", "adult": True, "goal": "clear her crew's name", "secret": "kept a backup log"},
            {"character_id": "hao", "adult": True, "goal": "prevent another wreck", "secret": "recognized the false signal"},
        ),
        scene_bibles=(
            {"scene_id": "storm_pier", "spatial_anchor": "beacon tower is northwest across the inlet"},
            {"scene_id": "beacon_room", "spatial_anchor": "backup circuit is beneath the west console"},
        ),
        story_beats=(
            {"beat_id": "signal", "scene_id": "storm_pier", "purpose": "choose evidence or rescue priority"},
            {"beat_id": "exposure", "scene_id": "beacon_room", "purpose": "pay the choice and reveal motive"},
        ),
        legal_choices={"signal": ("decode", "rescue"), "exposure": ("broadcast", "confront")},
        consequence_rules={
            "decode": {"known_fact_add": "the beacon log was forged", "time_delta": -1},
            "rescue": {"relationship_delta": {"hao": 2}, "resource_delta": {"flare": -1}},
            "broadcast": {"ending_unlock": "public_truth"},
            "confront": {"risk_delta": 2, "ending_unlock": "private_confession"},
        },
        reward_rules={"meaningful_feedback": ("evidence", "crew_trust", "spectacle", "ending_unlock")},
        ending_rules={
            "public_truth": {"requires": ("decode", "broadcast")},
            "private_confession": {"requires": ("confront",)},
        },
        style_profiles=style_profiles_v1(),
        asset_manifest=(
            {"asset_id": "synthetic_character_lin_v1", "role": "character_anchor", "synthetic": True},
            {"asset_id": "synthetic_tideglass_beacon_v1", "role": "scene_anchor", "synthetic": True},
        ),
        source_provenance={
            "source_id": "r176_synthetic_fixture_tideglass",
            "classification": "SYNTHETIC",
            "approved_for_reuse": True,
            "approval_record": "ISSUE-534-R176",
        },
        approval_status="approved",
    )


def approved_synthetic_script_packages() -> tuple[ScriptPackage, ScriptPackage]:
    """Return fresh immutable values so callers cannot share mutable state."""

    return (_archive_case(), _tideglass_signal())
