"""Director-contract determinism and fail-closed boundary tests (WB-S2).

These cases pin the checkpoint director's behavior that the coverage matrix
depends on, without modifying the director contract or its oracle. They are
consumer-side regressions only.
"""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

# Resolve imports without relying on discover's top-level directory, so the
# probe runs the same way from any discover depth.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (str(_REPO_ROOT), str(_REPO_ROOT / "tools" / "workbuddy")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from creative_runtime.contracts import StoryState  # noqa: E402
from creative_runtime.director import compile_director  # noqa: E402
from director_matrix import states  # noqa: E402


class DeterminismTest(unittest.TestCase):
    def test_same_state_compiles_same_plan(self) -> None:
        state = states.reachable_states()[0]
        first = compile_director(state)
        second = compile_director(state)
        self.assertEqual([shot.to_dict() for shot in first.shots], [shot.to_dict() for shot in second.shots])
        self.assertEqual(first.brief.brief_id, second.brief.brief_id)
        self.assertEqual(first.quality_report.to_dict(), second.quality_report.to_dict())

    def test_brief_id_encodes_scene_and_beat(self) -> None:
        for state in states.reachable_states():
            compilation = compile_director(state)
            self.assertTrue(compilation.brief.brief_id.startswith("brief_" + state.scene_id + "_" + state.beat_id))

    def test_shot_id_encodes_beat(self) -> None:
        state = StoryState(scene_id="synthetic_archive", beat_id="echo")
        compilation = compile_director(state)
        self.assertEqual(compilation.shots[0].shot_id, "shot_echo_01")

    def test_full_index_never_missing_asset(self) -> None:
        for state in states.reachable_states():
            report = compile_director(state).quality_report
            codes = {finding.code for finding in report.findings}
            self.assertNotIn("missing_asset", codes, states.state_key(state))
            self.assertTrue(report.can_generate)


class MissingAssetTest(unittest.TestCase):
    def test_missing_asset_is_explicit_and_blocks_generation(self) -> None:
        state = states.reachable_states()[0]
        for label, assets in states.missing_asset_variants():
            report = compile_director(state, assets).quality_report
            codes = {finding.code for finding in report.findings}
            self.assertIn("missing_asset", codes, label)
            self.assertFalse(report.can_generate, label)

    def test_missing_asset_does_not_throw(self) -> None:
        state = states.reachable_states()[0]
        _, assets = states.missing_asset_variants()[0]
        # compile_director must return a report, never raise on a missing asset.
        compilation = compile_director(state, assets)
        self.assertIsNotNone(compilation.quality_report)

    def test_missing_asset_still_produces_a_plan_for_audit(self) -> None:
        # The shot plan still compiles so the failure is inspectable, not a crash.
        state = states.reachable_states()[0]
        _, assets = states.missing_asset_variants()[0]
        compilation = compile_director(state, assets)
        self.assertEqual(len(compilation.shots), 1)


class FailClosedBoundaryTest(unittest.TestCase):
    def test_identity_not_adult_is_explicit(self) -> None:
        state = states.reachable_states()[0]
        assets = states.full_asset_index()
        assets["art_character_mira"]["adult"] = False
        report = compile_director(state, assets).quality_report
        codes = {finding.code for finding in report.findings}
        self.assertIn("identity_not_adult", codes)
        self.assertFalse(report.can_generate)

    def test_empty_asset_index_declares_every_missing_reference(self) -> None:
        state = states.reachable_states()[0]
        report = compile_director(state, {}).quality_report
        codes = {finding.code for finding in report.findings}
        self.assertEqual(codes, {"missing_asset"})

    def test_unknown_fact_in_boundary_fails_closed(self) -> None:
        # validate_compilation must reject a knowledge boundary that assigns a
        # fact absent from the state's own known_facts.
        from creative_runtime.contracts import DirectorBrief
        from creative_runtime.director import compile_shots, validate_compilation

        state = StoryState(scene_id="synthetic_archive", beat_id="arrival", known_facts=("a witness is inside",))
        brief = DirectorBrief(
            brief_id="brief_test",
            story_state=state,
            character_goals={"mira": "preserve safety"},
            knowledge_boundaries={"mira": ("unearned fact",)},
            spatial_facts=("axis:test",),
            content_rating="non_explicit",
        )
        shots = compile_shots(brief)
        report = validate_compilation(brief, shots, states.full_asset_index())
        codes = {finding.code for finding in report.findings}
        self.assertIn("knowledge_boundary_violation", codes)
        self.assertFalse(report.can_generate)

    def test_bad_duration_fails_closed(self) -> None:
        from dataclasses import replace

        from creative_runtime.director import validate_compilation

        state = states.reachable_states()[0]
        compilation = compile_director(state)
        bad_shot = replace(compilation.shots[0], duration_seconds=0)
        report = validate_compilation(compilation.brief, (bad_shot,), states.full_asset_index())
        codes = {finding.code for finding in report.findings}
        self.assertIn("duration_infeasible", codes)
        self.assertFalse(report.can_generate)


if __name__ == "__main__":
    unittest.main()
