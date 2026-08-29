from __future__ import annotations

from dataclasses import replace
import unittest

from creative_runtime.contracts import DirectorBrief, StoryState
from creative_runtime.director import compile_director, compile_shots, synthetic_asset_index, validate_compilation


class CreativeS03DirectorTests(unittest.TestCase):
    def test_valid_synthetic_state_compiles_to_generateable_plan(self) -> None:
        compilation = compile_director(
            StoryState(scene_id="synthetic_archive", beat_id="echo", known_facts=("a witness is inside",))
        )
        self.assertTrue(compilation.quality_report.can_generate)
        self.assertEqual(compilation.shots[0].beat_id, "echo")
        self.assertIn("art_scene_synthetic_archive", compilation.shots[0].reference_artifact_ids)

    def test_missing_asset_and_non_adult_identity_block_generation(self) -> None:
        state = StoryState(scene_id="synthetic_archive", beat_id="arrival")
        brief = compile_director(state).brief
        shots = compile_shots(brief)
        assets = synthetic_asset_index()
        assets.pop("art_scene_synthetic_archive")
        assets["art_character_mira"]["adult"] = False
        report = validate_compilation(brief, shots, assets)
        codes = {finding.code for finding in report.findings}
        self.assertFalse(report.can_generate)
        self.assertIn("missing_asset", codes)
        self.assertIn("identity_not_adult", codes)

    def test_unknown_knowledge_and_bad_duration_fail_closed(self) -> None:
        state = StoryState(scene_id="synthetic_archive", beat_id="arrival")
        valid = compile_director(state)
        invalid_brief = DirectorBrief(
            brief_id=valid.brief.brief_id,
            story_state=state,
            character_goals=valid.brief.character_goals,
            knowledge_boundaries={"mira": ("unearned fact",)},
            spatial_facts=(),
            content_rating="explicit",
        )
        invalid_shot = replace(valid.shots[0], duration_seconds=0, dominant_change="", axis="")
        report = validate_compilation(invalid_brief, (invalid_shot,), synthetic_asset_index())
        codes = {finding.code for finding in report.findings}
        self.assertFalse(report.can_generate)
        self.assertTrue({"knowledge_boundary_violation", "spatial_axis_missing", "content_rating_violation", "duration_infeasible", "dominant_change_missing"} <= codes)


if __name__ == "__main__":
    unittest.main()
