"""E22 focused synthetic-only tests for executable mutation and oracle evidence."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D2_ROOT = ROOT.parent / "0001-D2"
for item in (ROOT, D2_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from evaluation_v2_harness import assert_accepted_sut_fingerprint, run_evaluation
from independent_oracle import evaluate_episode
from metamorphic_properties import run_metamorphic_properties
from mutation_registry import execute_mutation_registry, mutation_registry
from synthetic_cases import (
    counterfactual_catalog, episode_catalog, execute_counterfactual, execute_episode, execute_negative,
    execute_scenario, invariant_catalog, negative_catalog, scenario_catalog,
)


class EvaluationV2Tests(unittest.TestCase):
    def test_sut_fingerprint_is_locked_to_accepted_gate_a(self):
        self.assertEqual(assert_accepted_sut_fingerprint(), "0bc7c7fba622440113bacb476c43f12245504fff35b3492969b485ac0f619afb")

    def test_all_72_synthetic_scenarios_have_valid_independent_accounting(self):
        scenarios = scenario_catalog()
        self.assertEqual(len(scenarios), 72)
        for spec in scenarios:
            with self.subTest(spec.scenario_id):
                run = execute_scenario(spec)
                self.assertTrue(evaluate_episode(run.episode_state).valid)

    def test_all_80_invariants_have_executable_oracles_and_test_ids(self):
        invariants = invariant_catalog()
        self.assertEqual(len(invariants), 80)
        self.assertTrue(all(item.failure_oracle_id.startswith("ORACLE-") and item.test_id for item in invariants))
        self.assertEqual(len({item.invariant_id for item in invariants}), 80)

    def test_all_37_negative_cases_fail_closed(self):
        negatives = negative_catalog()
        self.assertEqual(len(negatives), 37)
        for spec in negatives:
            with self.subTest(spec.negative_id):
                with self.assertRaises(ValueError):
                    execute_negative(spec)

    def test_all_24_episodes_continue_with_independent_accounting(self):
        episodes = episode_catalog()
        self.assertEqual(len(episodes), 24)
        for spec in episodes:
            with self.subTest(spec.episode_id):
                _one, two = execute_episode(spec)
                self.assertEqual(two.episode_state.step_index, 2)
                self.assertTrue(evaluate_episode(two.episode_state).valid)

    def test_all_36_counterfactual_pairs_change_one_action(self):
        pairs = counterfactual_catalog()
        self.assertEqual(len(pairs), 36)
        for spec in pairs:
            with self.subTest(spec.pair_id):
                result = execute_counterfactual(spec)
                self.assertEqual(len(result.changed_action_ids), 1)

    def test_all_mandatory_mutant_families_activate_and_are_killed(self):
        definitions = mutation_registry()
        activations, kills = execute_mutation_registry()
        self.assertEqual(len(definitions), 8)
        self.assertEqual(len(activations), len(definitions))
        self.assertTrue(all(item.behavior_changed and item.status == "KILLED" for item in activations))
        self.assertTrue(all(item.killed for item in kills))

    def test_all_metamorphic_properties_pass(self):
        reports = run_metamorphic_properties()
        self.assertEqual(len(reports), 8)
        self.assertTrue(all(item.passed for item in reports))

    def test_full_harness_reconciles_all_catalogs(self):
        summary, report = run_evaluation()
        self.assertEqual((summary.scenario_count, summary.invariant_count, summary.negative_count), (72, 80, 37))
        self.assertEqual((summary.episode_count, summary.counterfactual_count, summary.cross_family_count), (24, 36, 24))
        self.assertEqual(summary.mutation_score, 1.0)
        self.assertEqual(summary.survivors, ())
        self.assertEqual(summary.property_failures, ())
        self.assertEqual(len(report["mutation_kills"]), 8)


if __name__ == "__main__":
    unittest.main()
