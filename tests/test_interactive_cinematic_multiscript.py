"""A1 tests: versioned script selection and DirectorBrief/v2 context binding."""

from __future__ import annotations

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from apps.cli import creativectl
from creative_runtime.director_context import (
    DirectorContextViolation,
    campaign_id_for_ledger,
    compile_verified_director_v2,
    validate_director_brief_v2,
)
from creative_runtime.ledger import LedgerViolation
from creative_runtime.script_packages import (
    ScriptRegistryViolation,
    all_script_packages,
    script_catalog,
    script_for_ledger,
    script_package,
)


class InteractiveCinematicMultiscriptTests(unittest.TestCase):
    def test_registry_contains_only_approved_synthetic_packages_and_four_profiles(self) -> None:
        packages = all_script_packages()
        self.assertEqual(5, len(packages))
        self.assertEqual(5, len({package.script_id for package in packages}))
        self.assertTrue(all(package.approval_status == "approved_for_runtime" for package in packages))
        self.assertTrue(all(package.source_provenance == "synthetic_fixture" for package in packages))
        catalog = script_catalog()
        self.assertEqual("synthetic_registry_verified", catalog["status"])
        self.assertEqual(5, catalog["script_count"])
        self.assertEqual(
            {"cinematic_live_action", "stylized_3d", "japanese_animation", "ink_wash_animation"},
            {profile["style_profile_id"] for profile in catalog["style_profiles"]},
        )
        self.assertFalse(catalog["boundary"]["eustia_imported"])

    def test_new_script_initialization_and_old_scenario_initialization_have_same_immutable_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = creativectl.run(["--workspace", str(root / "legacy"), "init", "--scenario", "three_scene"])
            by_script = creativectl.run(
                [
                    "--workspace",
                    str(root / "script"),
                    "init",
                    "--script-id",
                    "synthetic-three-scene",
                    "--script-revision",
                    "SyntheticThreeScene/v1",
                ]
            )
            self.assertEqual(legacy["state"], by_script["state"])
            self.assertEqual("synthetic-three-scene", by_script["script_package"]["script_id"])
            for workspace in (root / "legacy", root / "script"):
                creativectl.run(["--workspace", str(workspace), "choose", "listen"])
                creativectl.run(["--workspace", str(workspace), "choose", "approach"])
            self.assertEqual(
                creativectl.run(["--workspace", str(root / "legacy"), "replay"])["state"],
                creativectl.run(["--workspace", str(root / "script"), "replay"])["state"],
            )

    def test_script_and_scenario_conflict_fail_closed_before_any_session_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "conflict"
            with self.assertRaisesRegex(LedgerViolation, "different initial story states"):
                creativectl.initialize(
                    workspace,
                    scenario="three_scene",
                    script_id="synthetic-harbor-protocol",
                    script_revision="SyntheticHarborProtocol/v1",
                )
            self.assertFalse((workspace / "session.json").exists())

    def test_director_v2_has_every_required_explicit_binding_and_preserves_legacy_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "night_signal"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            ledger = creativectl._load_session(workspace)
            compiled = compile_verified_director_v2(
                ledger,
                script_id="synthetic-night-signal",
                script_revision="SyntheticNightSignal/v1",
                style_profile_id="cinematic_live_action",
            )
            brief = compiled.brief_v2
            self.assertEqual("DirectorBrief/v2", brief.schema)
            self.assertEqual(campaign_id_for_ledger(ledger), brief.campaign_id)
            self.assertEqual(script_for_ledger(ledger).script_id, brief.script_id)
            self.assertEqual(64, len(brief.verified_story_state_hash))
            self.assertEqual(64, len(brief.continuity_ledger_hash))
            self.assertEqual(("art_scene_station_platform",), brief.scene_asset_refs)
            self.assertEqual(("cast_mira_synthetic_v1", "cast_player_synthetic_v1"), brief.cast_revision_ids)
            self.assertTrue(compiled.legacy_compilation.compilation.quality_report.can_generate)
            self.assertEqual(
                brief.narrative_brief,
                creativectl.compile_verified_director(ledger, graph=creativectl.graph_for_ledger(ledger)).compilation.brief,
            )

    def test_style_variants_keep_verified_story_and_camera_facts_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "harbor_protocol"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            ledger = creativectl._load_session(workspace)
            live = compile_verified_director_v2(
                ledger,
                script_id="synthetic-harbor-protocol",
                script_revision="SyntheticHarborProtocol/v1",
                style_profile_id="cinematic_live_action",
            )
            ink = compile_verified_director_v2(
                ledger,
                script_id="synthetic-harbor-protocol",
                script_revision="SyntheticHarborProtocol/v1",
                style_profile_id="ink_wash_animation",
            )
            self.assertNotEqual(live.brief_v2.style_profile_id, ink.brief_v2.style_profile_id)
            self.assertEqual(live.brief_v2.verified_story_state_hash, ink.brief_v2.verified_story_state_hash)
            self.assertEqual(live.brief_v2.continuity_ledger_hash, ink.brief_v2.continuity_ledger_hash)
            self.assertEqual(live.brief_v2.narrative_brief, ink.brief_v2.narrative_brief)
            self.assertEqual(live.legacy_compilation.compilation.shots, ink.legacy_compilation.compilation.shots)

    def test_mismatched_script_revision_style_campaign_and_tampered_context_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            ledger = creativectl._load_session(workspace)
            with self.assertRaisesRegex(DirectorContextViolation, "requested script does not match"):
                compile_verified_director_v2(
                    ledger,
                    script_id="synthetic-harbor-protocol",
                    script_revision="SyntheticHarborProtocol/v1",
                    style_profile_id="cinematic_live_action",
                )
            with self.assertRaisesRegex(DirectorContextViolation, "script_revision"):
                compile_verified_director_v2(
                    ledger,
                    script_id="synthetic-three-scene",
                    script_revision="not-a-revision",
                    style_profile_id="cinematic_live_action",
                )
            with self.assertRaisesRegex(DirectorContextViolation, "unknown style"):
                compile_verified_director_v2(
                    ledger,
                    script_id="synthetic-three-scene",
                    script_revision="SyntheticThreeScene/v1",
                    style_profile_id="unapproved_style",
                )
            with self.assertRaisesRegex(DirectorContextViolation, "campaign_id"):
                compile_verified_director_v2(
                    ledger,
                    script_id="synthetic-three-scene",
                    script_revision="SyntheticThreeScene/v1",
                    style_profile_id="cinematic_live_action",
                    campaign_id="camp_forged",
                )
            valid = compile_verified_director_v2(
                ledger,
                script_id="synthetic-three-scene",
                script_revision="SyntheticThreeScene/v1",
                style_profile_id="cinematic_live_action",
            )
            forged = replace(valid.brief_v2, scene_asset_refs=("art_scene_dawn_courtyard",))
            with self.assertRaisesRegex(DirectorContextViolation, "scene_asset_refs"):
                validate_director_brief_v2(forged, ledger, valid.legacy_compilation)
            with self.assertRaisesRegex(ScriptRegistryViolation, "unknown script_id"):
                script_package("not-registered")

    def test_cli_director_v2_exposes_a_machine_readable_verified_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--script-id", "synthetic-legacy-archive"])
            response = creativectl.run(
                [
                    "--workspace",
                    str(workspace),
                    "director-v2",
                    "--script-id",
                    "synthetic-legacy-archive",
                    "--script-revision",
                    "SyntheticLegacyArchive/v1",
                    "--style-profile-id",
                    "japanese_animation",
                ]
            )
            self.assertEqual("director_v2_verified", response["status"])
            self.assertEqual("DirectorBrief/v2", response["brief"]["schema"])
            self.assertEqual("japanese_animation", response["brief"]["style_profile_id"])
            self.assertTrue(response["quality_report"]["can_generate"])


if __name__ == "__main__":
    unittest.main()
