"""Semantic regression tests for the D2 synthetic evaluation harness."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT.parent / "0001-D2") not in sys.path:
    sys.path.insert(0, str(ROOT.parent / "0001-D2"))

from d2_game_core import SUBTYPE_FAMILY  # noqa: E402
from evaluation_harness import (  # noqa: E402
    build_counterfactual_pairs, build_scenarios, invariant_catalog, invariant_specs,
    mutation_sensitivity, negative_cases, normalized_evaluation_hash, run_all_scenarios,
    run_multistep_episodes,
)


class SemanticEvaluationHarnessTests(unittest.TestCase):
    def test_72_multi_agent_scenarios_cover_all_categories_and_families(self):
        scenarios = build_scenarios()
        self.assertEqual(72, len(scenarios))
        self.assertTrue(all(item.agent_count >= 2 for item in scenarios))
        self.assertGreaterEqual(sum(1 for item in scenarios if item.agent_count >= 3), 12)
        self.assertGreaterEqual(sum(1 for item in scenarios if item.category == "conflict"), 12)
        self.assertEqual({"retail", "institutional_quant", "active_capital", "policy_industrial_foreign_aggregate"}, {SUBTYPE_FAMILY[subtype].value for item in scenarios for subtype in item.participants})

    def test_each_result_contains_cross_agent_state_and_explicit_semantics(self):
        results = run_all_scenarios()
        self.assertEqual(72, len(results))
        self.assertTrue(all(len(item.run.final_agent_portfolios) >= 2 for item in results))
        self.assertTrue(all(len(item.run.total_system_state_hash) == 64 for item in results))
        conflict = next(item for item in results if item.scenario.category == "conflict")
        self.assertTrue(conflict.run.events[0].accepted)
        self.assertFalse(conflict.run.events[1].accepted)
        abstain = next(item for item in results if item.scenario.category == "incomplete_information")
        self.assertEqual("ABSTAINED", abstain.run.events[0].outcome_status)

    def test_80_semantic_invariants_are_requirement_linked(self):
        specs, catalog = invariant_specs(), invariant_catalog()
        self.assertEqual(80, len(specs))
        self.assertEqual(80, len(catalog))
        self.assertTrue(all(spec.requirement_id and spec.fixture_ids and spec.failure_oracle and spec.mapped_test_id for spec in specs))
        self.assertLessEqual(sum(1 for spec in specs if spec.family == "MUTATION"), 16)
        self.assertTrue(all(catalog.values()), {key: value for key, value in catalog.items() if not value})

    def test_36_counterfactual_pairs_and_24_stateful_episodes(self):
        pairs = build_counterfactual_pairs()
        episodes = run_multistep_episodes()
        self.assertEqual(36, len(pairs))
        self.assertTrue(all(left != right for left, right in pairs))
        self.assertEqual(24, len(episodes))
        self.assertTrue(all(run.causal_history_event_ids for run in episodes))
        self.assertTrue(all(run.total_system_state_hash for run in episodes))

    def test_36_negative_cases_fail_closed(self):
        cases = negative_cases()
        self.assertEqual(36, len(cases))
        for name, call in cases:
            try:
                result = call()
                if isinstance(result, bool):
                    self.assertFalse(result, name)
                elif hasattr(result, "events"):
                    self.assertFalse(result.events[0].accepted, name)
                else:
                    self.fail(f"negative case returned unexpected value: {name} -> {result!r}")
            except ValueError:
                pass

    def test_mutation_sensitivity_and_determinism(self):
        self.assertTrue(all(mutation_sensitivity().values()))
        self.assertEqual(normalized_evaluation_hash(), normalized_evaluation_hash())


if __name__ == "__main__":
    unittest.main(verbosity=2)
