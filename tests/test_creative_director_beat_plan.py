from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from creative_runtime import (
    MultiScriptDirectorCompiler,
    approved_synthetic_script_packages,
    flagship_story_fixture,
    load_catalog,
    materialize_catalog,
)
from creative_runtime.director_beat_plan import (
    DirectorBeatPlanViolation,
    DirectorBeatPlanner,
    STYLE_PRESENTATION,
    _digest,
    _without_hashes,
)


class DirectorBeatPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.package, self.graph, self.bibles = flagship_story_fixture()
        root = Path(self.temporary.name)
        relative = Path("catalog") / "flagship.json"
        materialize_catalog(root, relative, (self.package,))
        self.catalog = load_catalog(root, relative)
        self.compiler = MultiScriptDirectorCompiler(self.catalog)
        self.binding = self.compiler.select(
            script_id=self.package.script_id,
            script_revision=self.package.script_revision,
            package_hash=self.package.package_hash,
            style_profile_id="cinematic_live_action",
        )
        self.brief = self.compiler.compile(self.binding)
        self.planner = DirectorBeatPlanner(self.catalog, self.brief, self.graph, self.bibles)

    def assert_violation(self, code: str, operation) -> None:
        with self.assertRaises(DirectorBeatPlanViolation) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_all_twelve_choices_compile_and_inspect_deterministically(self) -> None:
        self.assertEqual(len(self.planner.list_choices()), 12)
        for choice_id, scene_id in self.planner.list_choices():
            first = self.planner.compile(choice_id, scene_id)
            second = self.planner.compile(choice_id, scene_id)
            self.assertEqual(first, second)
            self.assertIs(self.planner.inspect(first), first)
            self.assertEqual(len(first.beats), 6)
            self.assertEqual([item.order for item in first.beats], list(range(1, 7)))
            self.assertEqual(first.choice_id, choice_id)
            self.assertEqual(first.scene_id, scene_id)

    def test_all_twenty_four_outcomes_compile_and_inspect(self) -> None:
        count = 0
        for choice in self.graph.choices:
            for option in choice.options:
                preview = self.planner.compile_option_preview(choice.choice_id, choice.scene_id, option.option_id)
                self.assertIs(
                    self.planner.inspect_option_preview(choice.choice_id, choice.scene_id, preview), preview
                )
                self.assertEqual(preview.consequence_summary, option.consequence.summary)
                self.assertEqual(preview.change_dimensions, option.consequence.changes)
                self.assertTrue(preview.reward_tags)
                self.assertTrue(preview.cost_tags)
                count += 1
        self.assertEqual(count, 24)

    def test_four_styles_change_presentation_not_story_truth(self) -> None:
        choice = self.graph.choices[0]
        plans = []
        for style in STYLE_PRESENTATION:
            binding = self.compiler.select(
                script_id=self.package.script_id, script_revision=self.package.script_revision,
                package_hash=self.package.package_hash, style_profile_id=style,
            )
            brief = self.compiler.compile(binding)
            plan = DirectorBeatPlanner(self.catalog, brief, self.graph, self.bibles).compile(
                choice.choice_id, choice.scene_id
            )
            plans.append(plan)
        self.assertEqual({item.style_profile_id for item in plans}, set(STYLE_PRESENTATION))
        self.assertEqual(len({item.beats[0].presentation_intent for item in plans}), 4)
        story_truth = {
            tuple((preview.option_id, preview.consequence_summary, preview.change_dimensions)
                  for preview in item.outcome_previews)
            for item in plans
        }
        self.assertEqual(len(story_truth), 1)

    def test_plan_and_nested_values_are_immutable(self) -> None:
        choice = self.graph.choices[0]
        plan = self.planner.compile(choice.choice_id, choice.scene_id)
        with self.assertRaises(FrozenInstanceError):
            plan.choice_id = "forged"
        with self.assertRaises(FrozenInstanceError):
            plan.beats[0].objective = "forged"
        with self.assertRaises(FrozenInstanceError):
            plan.outcome_previews[0].option_label = "forged"

    def test_unknown_choice_scene_and_option_fail_closed(self) -> None:
        choice = self.graph.choices[0]
        self.assert_violation("CHOICE_UNKNOWN", lambda: self.planner.compile("missing", choice.scene_id))
        self.assert_violation("SCENE_OWNERSHIP", lambda: self.planner.compile(choice.choice_id, "wrong_scene"))
        self.assert_violation("OPTION_UNKNOWN", lambda: self.planner.compile_option_preview(
            choice.choice_id, choice.scene_id, "missing"
        ))

    def test_tampered_brief_graph_and_bibles_fail_closed(self) -> None:
        choice = self.graph.choices[0]
        bad_brief = replace(self.brief, compile_hash="0" * 64)
        with self.assertRaises(DirectorBeatPlanViolation):
            DirectorBeatPlanner(self.catalog, bad_brief, self.graph, self.bibles)
        bad_graph = replace(self.graph, package_hash="0" * 64)
        with self.assertRaises(DirectorBeatPlanViolation):
            DirectorBeatPlanner(self.catalog, self.brief, bad_graph, self.bibles)
        bad_bibles = replace(self.bibles, graph_hash="0" * 64)
        with self.assertRaises(DirectorBeatPlanViolation):
            DirectorBeatPlanner(self.catalog, self.brief, self.graph, bad_bibles)
        bad_character = replace(self.bibles.characters[0], appearance_anchor_asset_id="missing")
        bad_bibles = replace(self.bibles, characters=(bad_character, *self.bibles.characters[1:]))
        with self.assertRaises(DirectorBeatPlanViolation):
            DirectorBeatPlanner(self.catalog, self.brief, self.graph, bad_bibles)
        self.assertEqual(choice.order, 1)

    def test_missing_continuity_constraints_and_cross_script_substitution_fail_closed(self) -> None:
        character = replace(self.bibles.characters[0], knowledge_constraints=())
        bad_bibles = replace(self.bibles, characters=(character, *self.bibles.characters[1:]))
        with self.assertRaises(DirectorBeatPlanViolation):
            DirectorBeatPlanner(self.catalog, self.brief, self.graph, bad_bibles)
        scene = replace(self.bibles.scenes[0], staging_constraints=())
        bad_bibles = replace(self.bibles, scenes=(scene, *self.bibles.scenes[1:]))
        with self.assertRaises(DirectorBeatPlanViolation):
            DirectorBeatPlanner(self.catalog, self.brief, self.graph, bad_bibles)

        other = approved_synthetic_script_packages()[0]
        root = Path(self.temporary.name)
        other_path = Path("catalog") / "other.json"
        materialize_catalog(root, other_path, (other,))
        compiler = MultiScriptDirectorCompiler(load_catalog(root, other_path))
        binding = compiler.select(script_id=other.script_id, script_revision=other.script_revision,
                                  package_hash=other.package_hash, style_profile_id="cinematic_live_action")
        with self.assertRaises(DirectorBeatPlanViolation):
            DirectorBeatPlanner(load_catalog(root, other_path), compiler.compile(binding), self.graph, self.bibles)

    def test_recomputed_outer_hash_cannot_hide_plan_substitution(self) -> None:
        choice = self.graph.choices[0]
        plan = self.planner.compile(choice.choice_id, choice.scene_id)
        forged_beat = replace(plan.beats[0], objective="forged directing objective")
        forged = replace(plan, beats=(forged_beat, *plan.beats[1:]), plan_id="", plan_hash="")
        forged_hash = _digest(_without_hashes(forged))
        forged = replace(forged, plan_hash=forged_hash, plan_id=f"directorbeat_{forged_hash[:24]}")
        self.assert_violation("PLAN_SOURCE_SUBSTITUTION", lambda: self.planner.inspect(forged))

    def test_preview_substitution_fails_even_with_recomputed_preview_hash(self) -> None:
        choice = self.graph.choices[0]
        preview = self.planner.compile_option_preview(choice.choice_id, choice.scene_id, choice.options[0].option_id)
        forged = replace(preview, consequence_summary="forged", preview_hash="0" * 64)
        self.assert_violation(
            "PREVIEW_SOURCE_SUBSTITUTION",
            lambda: self.planner.inspect_option_preview(choice.choice_id, choice.scene_id, forged),
        )

    def test_no_player_session_job_or_provider_authority(self) -> None:
        names = set(vars(self.planner))
        for forbidden in ("player", "session", "campaign", "cursor", "ledger", "queue", "job", "provider"):
            self.assertFalse(any(forbidden in name.lower() for name in names))
        choice = self.graph.choices[0]
        before = self.planner.list_choices()
        self.planner.compile_option_preview(choice.choice_id, choice.scene_id, choice.options[0].option_id)
        self.assertEqual(before, self.planner.list_choices())


if __name__ == "__main__":
    unittest.main()
