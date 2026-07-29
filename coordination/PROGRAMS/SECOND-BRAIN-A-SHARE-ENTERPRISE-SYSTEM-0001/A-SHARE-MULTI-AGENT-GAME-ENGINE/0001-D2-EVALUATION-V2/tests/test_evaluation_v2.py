"""E23 synthetic tests for true-SUT mutation, catalog distinctness, and CI entry."""
from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D2_ROOT = ROOT.parent / "0001-D2"
for item in (ROOT, D2_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from catalog_validation import assert_catalogs_distinct, assert_distinct_semantic_signatures
from evaluation_v2_harness import assert_accepted_sut_fingerprint, run_evaluation
from independent_oracle import evaluate_episode
from metamorphic_properties import (
    property_function_map,
    run_metamorphic_properties,
    validate_transformation_registration,
)
from mutation_registry import (
    MutationDefinition,
    execute_mutation,
    execute_mutation_registry,
    mutation_registry,
    validate_true_sut_mutation,
)
from shadow_sut import SourceReplacement
from synthetic_cases import (
    counterfactual_catalog,
    cross_family_catalog,
    episode_catalog,
    execute_counterfactual,
    execute_episode,
    execute_negative,
    execute_scenario,
    invariant_catalog,
    negative_catalog,
    scenario_catalog,
)


class EvaluationV2Tests(unittest.TestCase):
    def test_sut_fingerprint_is_locked_to_accepted_gate_a(self):
        self.assertEqual(
            assert_accepted_sut_fingerprint(),
            "0bc7c7fba622440113bacb476c43f12245504fff35b3492969b485ac0f619afb",
        )

    def test_all_72_synthetic_scenarios_have_valid_independent_accounting(self):
        scenarios = scenario_catalog()
        self.assertEqual(len(scenarios), 72)
        for spec in scenarios:
            with self.subTest(spec.scenario_id):
                self.assertTrue(evaluate_episode(execute_scenario(spec).episode_state).valid)

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

    def test_all_36_counterfactual_pairs_change_exactly_one_action(self):
        pairs = counterfactual_catalog()
        self.assertEqual(len(pairs), 36)
        for spec in pairs:
            with self.subTest(spec.pair_id):
                self.assertEqual(len(execute_counterfactual(spec).changed_action_ids), 1)

    def test_catalogs_are_semantically_distinct_at_required_cardinality(self):
        pairs = tuple((item.mutant_id, item.paired_property_id) for item in mutation_registry())
        assert_catalogs_distinct(
            scenario_catalog(), invariant_catalog(), negative_catalog(), episode_catalog(),
            counterfactual_catalog(), cross_family_catalog(pairs),
        )

    def test_full_harness_reconciles_all_catalogs_and_actual_mutations(self):
        summary, report = run_evaluation()
        self.assertEqual((summary.scenario_count, summary.invariant_count, summary.negative_count), (72, 80, 37))
        self.assertEqual((summary.episode_count, summary.counterfactual_count, summary.cross_family_count), (24, 36, 24))
        self.assertEqual(summary.mutation_score, 1.0)
        self.assertEqual(summary.survivors, ())
        self.assertEqual(summary.property_failures, ())
        self.assertEqual(len(report["mutation_kills"]), 8)

    def test_registry_activation_records_source_hashes_not_posthoc_output(self):
        activations, kills = execute_mutation_registry()
        self.assertEqual(len(activations), 8)
        self.assertTrue(all(item.execution_mode == "SOURCE_DERIVED_SHADOW_MODULE" for item in activations))
        self.assertTrue(all(item.source_sha256 != item.mutant_source_sha256 for item in activations))
        self.assertTrue(all(item.behavior_changed and item.status == "KILLED" for item in activations))
        self.assertTrue(all(item.killed and not item.digest_only for item in kills))

    def test_rejects_posthoc_output_mutation_registration(self):
        definition = mutation_registry()[0]
        forbidden = replace(
            definition,
            replacements=(SourceReplacement("posthoc_output_after_sut", "before", "after"),),
        )
        with self.assertRaisesRegex(ValueError, "E23_POSTHOC_OUTPUT_MUTATION_FORBIDDEN"):
            validate_true_sut_mutation(forbidden)

    def test_rejects_no_source_delta_mutation_registration(self):
        definition = MutationDefinition(
            "MUT-TEST", "test", "FIX-TEST", "ORACLE-TEST", "MP-TEST", (),
        )
        with self.assertRaisesRegex(ValueError, "E23_MUTATION_REQUIRES_SOURCE_DERIVED_SEAM"):
            validate_true_sut_mutation(definition)

    def test_rejects_identity_metamorphic_transformation(self):
        with self.assertRaisesRegex(ValueError, "E23_IDENTITY_OR_NOOP_METAMORPHIC_TRANSFORMATION_FORBIDDEN"):
            validate_transformation_registration("MP-TEST", {"same": 1}, {"same": 1})

    def test_ci_workflow_invokes_focused_suite_and_public_runner(self):
        workflow = ROOT.parents[4] / ".github" / "workflows" / "phase3-integrated-offline-memory.yml"
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("Run E23 Evaluation V2 true-SUT mutation suite", content)
        self.assertIn("python -B tests/test_evaluation_v2.py", content)
        self.assertIn("python -B tests/run_evaluation_v2.py", content)


def _make_mutation_test(definition):
    def test(self):
        execution = execute_mutation(definition, variant=2)
        self.assertTrue(execution.activation.behavior_changed)
        self.assertEqual(execution.activation.status, "KILLED")
        self.assertTrue(execution.kill.killed)
        self.assertFalse(execution.kill.digest_only)
        self.assertEqual(execution.kill.oracle_id, definition.oracle_id)
    return test


def _make_property_test(property_id, function):
    def test(self):
        report = function(variant=2)
        self.assertTrue(report.baseline_passed)
        self.assertTrue(report.mutant_detected)
        self.assertTrue(report.passed)
        self.assertEqual(report.property_id, property_id)
    return test


def _make_duplicate_catalog_test(kind, factory, minimum):
    def test(self):
        rows = factory()
        self.assertGreaterEqual(len(rows), minimum)
        with self.assertRaisesRegex(AssertionError, "E23_DUPLICATE_NORMALIZED_SEMANTIC_SIGNATURE:" + kind):
            assert_distinct_semantic_signatures(kind, rows + (rows[0],), minimum)
    return test


for _definition in mutation_registry():
    setattr(
        EvaluationV2Tests,
        "test_true_sut_mutation_" + _definition.mutant_id.lower().replace("-", "_"),
        _make_mutation_test(_definition),
    )

for _property_id, _function in property_function_map().items():
    setattr(
        EvaluationV2Tests,
        "test_metamorphic_" + _property_id.lower().replace("-", "_"),
        _make_property_test(_property_id, _function),
    )

_DUPLICATE_CATALOGS = (
    ("scenarios", scenario_catalog, 72),
    ("invariants", invariant_catalog, 80),
    ("negatives", negative_catalog, 37),
    ("episodes", episode_catalog, 24),
    ("counterfactuals", counterfactual_catalog, 36),
    ("cross_family", lambda: cross_family_catalog(tuple((item.mutant_id, item.paired_property_id) for item in mutation_registry())), 24),
)
for _kind, _factory, _minimum in _DUPLICATE_CATALOGS:
    setattr(EvaluationV2Tests, "test_rejects_duplicate_" + _kind, _make_duplicate_catalog_test(_kind, _factory, _minimum))


if __name__ == "__main__":
    unittest.main()
