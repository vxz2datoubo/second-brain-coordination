from __future__ import annotations

from dataclasses import replace
import unittest

from creative_runtime.contracts import DirectorBrief, StoryState
from creative_runtime.director import compile_director, compile_shots, select_director_skills, synthetic_asset_index, validate_compilation


class CreativeS03DirectorTests(unittest.TestCase):
    def test_valid_synthetic_state_compiles_to_generateable_plan(self) -> None:
        compilation = compile_director(
            StoryState(scene_id="synthetic_archive", beat_id="echo", known_facts=("a witness is inside",))
        )
        self.assertTrue(compilation.quality_report.can_generate)
        self.assertEqual(compilation.shots[0].beat_id, "echo")
        self.assertEqual(len(compilation.shots), 2)
        self.assertEqual(sum(shot.duration_seconds for shot in compilation.shots), 13)
        self.assertEqual(
            compilation.quality_report.metrics.to_dict(),
            {
                "shot_count": 2,
                "total_duration_seconds": 13,
                "hard_finding_count": 0,
                "activated_skill_count": 2,
                "referenced_asset_count": 3,
            },
        )
        self.assertIn("art_scene_synthetic_archive", compilation.shots[0].reference_artifact_ids)

    def test_three_scene_state_uses_matching_scene_asset_and_axis_for_every_shot(self) -> None:
        compilation = compile_director(StoryState(scene_id="interior_archive", beat_id="threshold"))
        self.assertTrue(compilation.quality_report.can_generate)
        self.assertTrue(all(shot.axis == "entry-hall-to-record-room" for shot in compilation.shots))
        self.assertTrue(all("art_scene_interior_archive" in shot.reference_artifact_ids for shot in compilation.shots))

    def test_skill_activation_is_minimal_and_has_recorded_reasons(self) -> None:
        initial = StoryState(scene_id="archive_gate", beat_id="arrival")
        initial_ids, initial_reasons = select_director_skills(initial)
        self.assertEqual(initial_ids, ("scene_continuity",))
        self.assertEqual(set(initial_reasons), {"scene_continuity"})
        state = StoryState(
            scene_id="interior_archive",
            beat_id="accord",
            relationships={"mira": 2},
            known_facts=("a witness is inside",),
            flags={"handoff": "promised"},
        )
        compiled = compile_director(state)
        self.assertEqual(
            compiled.brief.activated_skill_ids,
            ("handoff_consequence", "knowledge_boundary", "relationship_consequence", "scene_continuity"),
        )
        self.assertEqual(set(compiled.brief.skill_trigger_reasons), set(compiled.brief.activated_skill_ids))

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

    def test_cross_shot_continuity_and_budget_violations_fail_closed(self) -> None:
        valid = compile_director(StoryState(scene_id="archive_gate", beat_id="echo"))
        wrong_scene = replace(valid.shots[0], shot_id=valid.shots[1].shot_id, axis="wrong-axis", beat_id="arrival", duration_seconds=16, reference_artifact_ids=("art_scene_dawn_courtyard",))
        report = validate_compilation(valid.brief, (wrong_scene, valid.shots[1]), synthetic_asset_index())
        codes = {finding.code for finding in report.findings}
        self.assertFalse(report.can_generate)
        self.assertTrue({"duplicate_shot_id", "duration_budget_exceeded", "spatial_axis_mismatch", "shot_beat_mismatch", "scene_reference_missing", "scene_reference_mismatch", "character_reference_missing"} <= codes)
        self.assertGreater(report.metrics.hard_finding_count, 0)
        self.assertEqual(report.metrics.total_duration_seconds, 24)

    def test_unjustified_or_missing_director_skill_fails_closed(self) -> None:
        valid = compile_director(StoryState(scene_id="archive_gate", beat_id="arrival"))
        invalid = replace(
            valid.brief,
            activated_skill_ids=("knowledge_boundary", "scene_continuity"),
            skill_trigger_reasons={"knowledge_boundary": "invented", "scene_continuity": "invented"},
        )
        report = validate_compilation(invalid, valid.shots, synthetic_asset_index())
        codes = {finding.code for finding in report.findings}
        self.assertFalse(report.can_generate)
        self.assertTrue({"skill_activation_mismatch", "skill_trigger_reason_mismatch"} <= codes)

    def test_timeline_bound_brief_requires_hash_and_consequence_and_expresses_it(self) -> None:
        state = StoryState(scene_id="interior_archive", beat_id="accord", relationships={"mira": 2})
        invalid = compile_director(state, source_timeline_hash="too-short", story_consequence={})
        self.assertFalse(invalid.quality_report.can_generate)
        valid = compile_director(
            state,
            source_timeline_hash="a" * 64,
            story_consequence={"relationship_delta": {"mira": 1}, "risk_delta": -1, "flag_changes": {"handoff": "promised"}},
        )
        self.assertTrue(valid.quality_report.can_generate)
        self.assertIn("relationship shift", valid.shots[-1].dominant_change)
        self.assertIn("risk level", valid.shots[-1].dominant_change)


if __name__ == "__main__":
    unittest.main()
