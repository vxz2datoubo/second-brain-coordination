from __future__ import annotations

from dataclasses import replace
import unittest

from creative_runtime import (
    StoryGraphViolation,
    compile_consequence_coverage,
    flagship_story_fixture,
    validate_graph_for_package,
    validate_story_graph,
)


class StoryGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.package, self.graph, _ = flagship_story_fixture()

    def assert_violation(self, code, operation) -> None:
        with self.assertRaises(StoryGraphViolation) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_flagship_structure_is_exact_and_deterministic(self) -> None:
        _, second, _ = flagship_story_fixture()
        self.assertEqual((len(self.graph.acts), len(self.graph.chapters), len(self.graph.choices)), (3, 6, 12))
        self.assertEqual(self.graph.graph_hash, second.graph_hash)
        self.assertIs(validate_graph_for_package(self.graph, self.package), self.graph)

    def test_every_option_has_visible_hashed_consequence(self) -> None:
        coverage = compile_consequence_coverage(self.graph)
        self.assertEqual(coverage.option_count, 24)
        self.assertEqual(len(coverage.option_hashes), 24)
        self.assertTrue(all(value > 0 for value in coverage.dimension_counts.values()))
        self.assertTrue(all(len(value) == 64 for value in coverage.option_hashes.values()))

    def test_dangling_edge_fails_closed(self) -> None:
        first = self.graph.choices[0]
        bad_option = replace(first.options[0], next_choice_id="missing")
        bad = replace(self.graph, choices=(replace(first, options=(bad_option, first.options[1])), *self.graph.choices[1:]))
        self.assert_violation("DANGLING_EDGE", lambda: validate_story_graph(bad))

    def test_jump_and_cycle_fail_closed(self) -> None:
        first = self.graph.choices[0]
        jump = replace(first.options[0], next_choice_id=self.graph.choices[2].choice_id)
        bad = replace(self.graph, choices=(replace(first, options=(jump, first.options[1])), *self.graph.choices[1:]))
        self.assert_violation("ILLEGAL_JUMP_OR_CYCLE", lambda: validate_story_graph(bad))

    def test_missing_consequence_and_duplicate_option_fail_closed(self) -> None:
        first = self.graph.choices[0]
        missing = replace(first.options[0], consequence=replace(first.options[0].consequence, changes=()))
        bad = replace(self.graph, choices=(replace(first, options=(missing, first.options[1])), *self.graph.choices[1:]))
        self.assert_violation("CONSEQUENCE_MISSING", lambda: validate_story_graph(bad))
        second = self.graph.choices[1]
        duplicate = replace(second.options[0], option_id=first.options[0].option_id)
        choices = (first, replace(second, options=(duplicate, second.options[1])), *self.graph.choices[2:])
        self.assert_violation("OPTION_ID", lambda: validate_story_graph(replace(self.graph, choices=choices)))

    def test_early_ending_and_cross_script_identity_fail_closed(self) -> None:
        first = self.graph.choices[0]
        ending = replace(first.options[0], next_choice_id=None, ending_id=self.graph.ending_ids[0])
        bad = replace(self.graph, choices=(replace(first, options=(ending, first.options[1])), *self.graph.choices[1:]))
        self.assert_violation("EARLY_ENDING", lambda: validate_story_graph(bad))
        self.assert_violation("CROSS_SCRIPT_IDENTITY", lambda: validate_graph_for_package(replace(self.graph, script_id="other"), self.package))

    def test_package_legal_choice_substitution_fails_closed(self) -> None:
        legal = dict(self.package.legal_choices)
        legal[self.graph.entry_choice_id] = ("forged",)
        forged = replace(self.package, legal_choices=legal)
        self.assert_violation("PACKAGE_OPTION_REFERENCE", lambda: validate_graph_for_package(self.graph, forged))


if __name__ == "__main__":
    unittest.main()
