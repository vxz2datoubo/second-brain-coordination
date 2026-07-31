"""E23 synthetic tests for true-SUT mutation, catalog distinctness, and CI entry."""
from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
D2_ROOT = ROOT.parent / "0001-D2"
for item in (ROOT, D2_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from catalog_validation import assert_catalogs_distinct, assert_distinct_execution_cases
from evaluation_v2_harness import (
    _counterfactual_catalog_case,
    assert_accepted_sut_fingerprint,
    run_evaluation,
)
from invariant_registry import (
    InvariantRule,
    NamedOracleEvidence,
    execute_controlled_violation,
    execute_invariant_rule,
    invariant_registry,
    rule_for,
    validate_invariant_registry,
)
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
from portable_archive_evidence import (
    ArtifactReceipt,
    ArchiveReceipt,
    CommandReceipt,
    EVALUATION_RELATIVE_ROOT,
    require_within_archive_root,
    validate_archive_receipts,
)
from receipt_validation import WPDCR_REQUIRED_SECTIONS, validate_completion_evidence
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

    def test_all_80_invariants_dispatch_predicates_and_named_oracles(self):
        invariants = invariant_catalog()
        self.assertEqual(len(invariants), 80)
        self.assertTrue(all(item.failure_oracle_id == "ORACLE-" + item.predicate_id and item.test_id for item in invariants))
        self.assertEqual(len({item.invariant_id for item in invariants}), 80)
        summary, report = run_evaluation()
        self.assertEqual(summary.invariant_count, 80)
        self.assertTrue(all(
            row["passed"]
            and row["controlled_violation_rejected"]
            and row["oracle_detects_controlled_violation"]
            and row["oracle_reason_codes"]
            and row["valid_artifact_sha256"] != row["violating_artifact_sha256"]
            and row["violating_artifact_sha256"] == row["oracle_artifact_sha256"]
            for row in report["invariants"]
        ))
        with self.assertRaisesRegex(ValueError, "UNKNOWN_INVARIANT_PREDICATE"):
            rule_for("NOT_REGISTERED")

    def test_invariant_registry_fails_closed_for_orphan_and_incomplete_rules(self):
        registry = invariant_registry()
        with self.assertRaisesRegex(AssertionError, "E25_UNMAPPED_INVARIANT_PREDICATE"):
            validate_invariant_registry(("HAS_EPISODE", "NOT_REGISTERED"), registry)
        broken = dict(registry)
        original = broken["HAS_EPISODE"]
        broken["HAS_EPISODE"] = InvariantRule(
            original.predicate_id,
            original.failure_oracle_id,
            original.predicate,
            None,
            original.failure_oracle,
        )
        with self.assertRaisesRegex(AssertionError, "E25_INCOMPLETE_INVARIANT_RULE"):
            validate_invariant_registry(tuple(sorted(registry)), broken)

    def test_controlled_violation_cannot_be_replaced_with_a_valid_artifact(self):
        valid_run = execute_scenario(scenario_catalog()[0])
        rule = rule_for("HAS_EPISODE")
        decorative = replace(rule, controlled_violation=lambda run: run)
        with self.assertRaisesRegex(AssertionError, "DECORATIVE_OR_NON_VIOLATING_FIXTURE:HAS_EPISODE"):
            execute_invariant_rule(decorative, valid_run)

    def test_oracle_independence_guard_rejects_a_paired_predicate_closure(self):
        original = rule_for("HAS_EPISODE")

        def self_verifying_oracle(run):
            return NamedOracleEvidence(
                "ORACLE-HAS_EPISODE",
                not original.predicate(run),
                ("FORGED_SELF_VERIFICATION",),
                "forged",
            )

        corrupted = dict(invariant_registry())
        corrupted[original.predicate_id] = replace(original, failure_oracle=self_verifying_oracle)
        with self.assertRaisesRegex(AssertionError, "E26_ORACLE_DEPENDS_ON_PAIRED_PREDICATE:HAS_EPISODE"):
            validate_invariant_registry(tuple(sorted(corrupted)), corrupted)

    def test_harness_injects_declared_spec_disagreement_without_changing_execution_signature(self):
        actual_spec = counterfactual_catalog()[0]
        misleading_spec = replace(
            actual_spec,
            variant=999,
            semantic_input=(("quantity", 999999), ("side", "FORGED")),
            expected_relation=(("changed_action_count", 999999),),
        )

        _baseline_summary, baseline_report = run_evaluation()
        _declared_summary, declared_report = run_evaluation(
            declared_counterfactual_specs={actual_spec.pair_id: misleading_spec},
        )
        baseline_trace = next(
            row for row in baseline_report["catalog_signatures"]["counterfactuals"]
            if row["id"] == actual_spec.pair_id
        )
        declared_trace = next(
            row for row in declared_report["catalog_signatures"]["counterfactuals"]
            if row["id"] == actual_spec.pair_id
        )
        self.assertEqual(baseline_trace["execution_signatures"], declared_trace["execution_signatures"])
        self.assertTrue(declared_trace["specification_disagreement"])
        self.assertEqual(declared_trace["declared_specification"]["variant"], 999)
        self.assertIn("999999", repr(declared_trace["declared_specification"]))
        self.assertNotIn("999999", repr(declared_trace["executed_input"]))
        self.assertNotIn("FORGED", repr(declared_trace["observed_relation"]))

    def test_actual_counterfactual_execution_change_changes_execution_signature(self):
        actual_spec = counterfactual_catalog()[0]
        changed_execution_spec = replace(actual_spec, variant=2, changed_assumption_id="assumption:cf-002")
        actual_trace = _counterfactual_catalog_case(execute_counterfactual(actual_spec), actual_spec)
        changed_trace = _counterfactual_catalog_case(
            execute_counterfactual(changed_execution_spec),
            changed_execution_spec,
        )
        assert_distinct_execution_cases("counterfactual-proof", [actual_trace, changed_trace])
        self.assertNotEqual(
            actual_trace["execution_signatures"],
            changed_trace["execution_signatures"],
        )

    def test_archive_receipts_fail_closed_for_independent_root_or_artifact_disagreement(self):
        def receipt(run_id, commit):
            return ArchiveReceipt(
                run_id,
                commit,
                "archive-sha-identical",
                123,
                10,
                "root-" + run_id,
                "root-path-hash-" + run_id,
                (
                    ArtifactReceipt("tests/test_evaluation_v2.py", "artifact-test", 100),
                    ArtifactReceipt("tests/run_evaluation_v2.py", "artifact-runner", 200),
                ),
                (
                    CommandReceipt("focused_tests", ("python", "-B", "tests/test_evaluation_v2.py"), EVALUATION_RELATIVE_ROOT.as_posix(), "tests/test_evaluation_v2.py", 0, "test", ""),
                    CommandReceipt("public_runner", ("python", "-B", "tests/run_evaluation_v2.py"), EVALUATION_RELATIVE_ROOT.as_posix(), "tests/run_evaluation_v2.py", 0, "runner", ""),
                ),
            )

        expected_commit = "a" * 40
        valid = tuple(receipt("archive-run-%03d" % index, expected_commit) for index in (1, 2, 3))
        validate_archive_receipts(valid, expected_commit)
        with self.assertRaisesRegex(AssertionError, "E26_ARCHIVE_COMMIT_MISMATCH"):
            validate_archive_receipts(valid[:2] + (receipt("archive-run-003", "b" * 40),), expected_commit)
        with self.assertRaisesRegex(AssertionError, "E26_ARCHIVE_ROOT_NOT_DISTINCT"):
            validate_archive_receipts((valid[0], valid[0], valid[2]), expected_commit)
        with self.assertRaisesRegex(AssertionError, "E28_ARCHIVE_ARTIFACT_MANIFEST_DRIFT"):
            drifted = replace(
                valid[2],
                artifacts=(ArtifactReceipt("tests/test_evaluation_v2.py", "artifact-test", 101),),
            )
            validate_archive_receipts(valid[:2] + (drifted,), expected_commit)
        with self.assertRaisesRegex(AssertionError, "E28_ARCHIVE_ROOT_PATH_NOT_DISTINCT"):
            repeated_path = replace(valid[2], root_path_sha256=valid[0].root_path_sha256)
            validate_archive_receipts(valid[:2] + (repeated_path,), expected_commit)
        with self.assertRaisesRegex(AssertionError, "E28_ARCHIVE_ARTIFACT_MANIFEST_MISSING"):
            missing_artifacts = replace(valid[2], artifacts=())
            validate_archive_receipts(valid[:2] + (missing_artifacts,), expected_commit)

    def test_archive_execution_path_cannot_escape_extracted_root(self):
        with TemporaryDirectory() as temporary:
            archive_root = Path(temporary) / "archive"
            archive_root.mkdir()
            require_within_archive_root(archive_root, archive_root / "inside.py")
            with self.assertRaisesRegex(RuntimeError, "E26_ARCHIVE_EXECUTION_ESCAPES_ROOT"):
                require_within_archive_root(archive_root, archive_root.parent / "outside.py")

    def test_completion_evidence_rejects_missing_and_placeholder_fields(self):
        with self.assertRaisesRegex(ValueError, "E26_COMPLETION_EVIDENCE_MISSING"):
            validate_completion_evidence({})
        carrier = {
            "task_id": "E26", "route_epoch": 27, "completion_signal": "SIGNAL",
            "pull_request": 106, "issue": 23, "branch": "codex/example",
            "reviewed_base": "a" * 40, "remote_main_before": "b" * 40,
            "remote_main_after": "c" * 40, "tested_commit": "d" * 40,
            "tested_parent": "e" * 40, "receipt_commit": "THIS_COMMIT_AFTER_PUSH",
            "changed_files": [], "commands": [], "unknowns": [], "negative_findings": [],
            "archive_evidence": {"exact_commit": "d" * 40},
            "wpdcr": {section: {"present": True} for section in WPDCR_REQUIRED_SECTIONS},
        }
        with self.assertRaisesRegex(ValueError, "E26_COMPLETION_EVIDENCE_PLACEHOLDER:receipt_commit"):
            validate_completion_evidence(carrier)

    def test_completion_evidence_fails_closed_for_wpdcr_and_archive_root_contracts(self):
        commit = "d" * 40

        def archive_receipt(index, *, root_id=None, root_path_sha256=None, artifact_size=10, script="tests/run_evaluation_v2.py"):
            return {
                "archive_run_id": "archive-run-%03d" % index,
                "commit": commit,
                "archive_sha256": "archive-identical",
                "archive_size_bytes": 100,
                "extracted_file_count": 2,
                "root_id": "root-%03d" % index if root_id is None else root_id,
                "root_path_sha256": "root-path-%03d" % index if root_path_sha256 is None else root_path_sha256,
                "artifacts": [
                    {"relative_path": "tests/test_evaluation_v2.py", "sha256": "test", "size_bytes": artifact_size},
                ],
                "commands": [
                    {
                        "name": "public_runner",
                        "command": ["python", "-B", script],
                        "working_directory_relative": EVALUATION_RELATIVE_ROOT.as_posix(),
                        "script_relative_path": script,
                        "exit_code": 0,
                        "stdout_sha256": "stdout",
                        "stderr_sha256": "stderr",
                    },
                ],
            }

        carrier = {
            "task_id": "E28", "route_epoch": 29, "completion_signal": "SIGNAL",
            "pull_request": 106, "issue": 23, "branch": "codex/example",
            "reviewed_base": "a" * 40, "remote_main_before": "b" * 40,
            "remote_main_after": "c" * 40, "tested_commit": commit,
            "tested_parent": "e" * 40, "receipt_commit": "f" * 40,
            "changed_files": [], "commands": [], "unknowns": [], "negative_findings": [],
            "archive_evidence": {
                "exact_commit": commit,
                "archive_receipts": [archive_receipt(index) for index in (1, 2, 3)],
            },
            "wpdcr": {section: {"present": True} for section in WPDCR_REQUIRED_SECTIONS},
        }
        validate_completion_evidence(carrier)
        with self.assertRaisesRegex(ValueError, "E28_COMPLETION_EVIDENCE_COMPLETION_SIGNAL_MISMATCH"):
            validate_completion_evidence(carrier, expected_completion_signal="OTHER_SIGNAL")
        missing_wpdcr = dict(carrier)
        missing_wpdcr["wpdcr"] = {section: {"present": True} for section in WPDCR_REQUIRED_SECTIONS - {"next_action_and_gate"}}
        with self.assertRaisesRegex(ValueError, "E28_WPDCR_REQUIRED_SECTION_MISSING:next_action_and_gate"):
            validate_completion_evidence(missing_wpdcr)
        repeated_root = dict(carrier)
        repeated_root["archive_evidence"] = {
            "exact_commit": commit,
            "archive_receipts": [
                archive_receipt(1), archive_receipt(2, root_id="root-001"), archive_receipt(3),
            ],
        }
        with self.assertRaisesRegex(ValueError, "E28_COMPLETION_EVIDENCE_ARCHIVE_ROOT_NOT_DISTINCT"):
            validate_completion_evidence(repeated_root)
        missing_root = dict(carrier)
        missing_root["archive_evidence"] = {
            "exact_commit": commit,
            "archive_receipts": [
                archive_receipt(1), archive_receipt(2, root_path_sha256=""), archive_receipt(3),
            ],
        }
        with self.assertRaisesRegex(ValueError, "E28_COMPLETION_EVIDENCE_ARCHIVE_ROOT_MISSING"):
            validate_completion_evidence(missing_root)
        external_command = dict(carrier)
        external_command["archive_evidence"] = {
            "exact_commit": commit,
            "archive_receipts": [
                archive_receipt(1), archive_receipt(2), archive_receipt(3, script="C:/outside.py"),
            ],
        }
        with self.assertRaisesRegex(ValueError, "E28_COMPLETION_EVIDENCE_ARCHIVE_COMMAND_ESCAPES_ROOT"):
            validate_completion_evidence(external_command)
        artifact_drift = dict(carrier)
        artifact_drift["archive_evidence"] = {
            "exact_commit": commit,
            "archive_receipts": [
                archive_receipt(1), archive_receipt(2), archive_receipt(3, artifact_size=11),
            ],
        }
        with self.assertRaisesRegex(ValueError, "E28_COMPLETION_EVIDENCE_ARCHIVE_ARTIFACT_MANIFEST_DRIFT"):
            validate_completion_evidence(artifact_drift)

    def test_trace_catalogs_reuse_the_single_actual_episode_and_counterfactual_execution(self):
        with patch("evaluation_v2_harness.execute_episode", wraps=execute_episode) as episode_call, patch(
            "evaluation_v2_harness.execute_counterfactual", wraps=execute_counterfactual,
        ) as counterfactual_call:
            _summary, report = run_evaluation()
        self.assertEqual(episode_call.call_count, 24)
        self.assertEqual(counterfactual_call.call_count, 32)
        self.assertTrue(all(
            row["observed_relation"]["final_state_hash"]
            for row in report["catalog_signatures"]["episodes"]
        ))
        self.assertTrue(all(
            row["observed_relation"]["baseline_state_hash"]
            and row["observed_relation"]["alternative_state_hash"]
            for row in report["catalog_signatures"]["counterfactuals"]
        ))

    def test_catalog_signatures_change_only_when_actual_consumed_input_or_observation_changes(self):
        base = {"id": "base", "executed_input": {"quantity": 1}, "observed_relation": {"accepted": True}}
        changed_input = {"id": "renamed", "executed_input": {"quantity": 2}, "observed_relation": {"accepted": True}}
        changed_relation = {"id": "same-input", "executed_input": {"quantity": 1}, "observed_relation": {"accepted": False}}
        assert_distinct_execution_cases("trace", [base, changed_input, changed_relation])
        self.assertNotEqual(base["execution_signatures"][0], changed_input["execution_signatures"][0])
        self.assertNotEqual(base["execution_signatures"][1], changed_relation["execution_signatures"][1])
        duplicate = {"id": "formula-label-only", "executed_input": {"quantity": 1}, "observed_relation": {"accepted": True}}
        with self.assertRaisesRegex(AssertionError, "E24_DUPLICATE_EXECUTION_SIGNATURE:trace"):
            assert_distinct_execution_cases("trace", [base, duplicate])

    def test_unique_negative_families_fail_closed(self):
        negatives = negative_catalog()
        self.assertEqual(len(negatives), 10)
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

    def test_all_32_counterfactual_pairs_change_exactly_one_action(self):
        pairs = counterfactual_catalog()
        self.assertEqual(len(pairs), 32)
        for spec in pairs:
            with self.subTest(spec.pair_id):
                self.assertEqual(len(execute_counterfactual(spec).changed_action_ids), 1)

    def test_catalogs_are_semantically_distinct_at_required_cardinality(self):
        pairs = tuple((item.mutant_id, item.paired_property_id) for item in mutation_registry())
        summary, report = run_evaluation()
        self.assertEqual(summary.canonical_report_sha256, report["canonical_report_sha256"] if "canonical_report_sha256" in report else summary.canonical_report_sha256)
        for kind, rows in report["catalog_signatures"].items():
            with self.subTest(kind):
                self.assertTrue(rows)
                self.assertTrue(all("execution_signatures" in row for row in rows))

    def test_full_harness_reconciles_all_catalogs_and_actual_mutations(self):
        summary, report = run_evaluation()
        self.assertEqual((summary.scenario_count, summary.invariant_count, summary.negative_count), (72, 80, 10))
        self.assertEqual((summary.episode_count, summary.counterfactual_count, summary.cross_family_count), (24, 32, 24))
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


def _make_execution_duplicate_test(kind):
    def test(self):
        rows = [
            {"id": "first", "executed_input": {"consumed": 1}, "observed_relation": {"result": "same"}},
            {"id": "renamed-only", "executed_input": {"consumed": 1}, "observed_relation": {"result": "same"}},
        ]
        with self.assertRaisesRegex(AssertionError, "E24_DUPLICATE_EXECUTION_SIGNATURE:" + kind):
            assert_distinct_execution_cases(kind, rows)
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

for _kind in ("scenarios", "invariants", "negatives", "episodes", "counterfactuals", "cross_family"):
    setattr(EvaluationV2Tests, "test_rejects_metadata_only_duplicate_" + _kind, _make_execution_duplicate_test(_kind))


def _make_controlled_violation_test(predicate_id):
    def test(self):
        valid_run = execute_scenario(scenario_catalog()[0])
        evidence = execute_controlled_violation(predicate_id, valid_run)
        self.assertTrue(evidence.valid_predicate_passed)
        self.assertFalse(evidence.violating_predicate_passed)
        self.assertTrue(evidence.oracle.detected)
        self.assertTrue(evidence.oracle.reason_codes)
        self.assertNotEqual(evidence.valid_artifact_sha256, evidence.violating_artifact_sha256)
        self.assertEqual(evidence.violating_artifact_sha256, evidence.oracle.artifact_sha256)
    return test


def _make_direct_oracle_tamper_test(predicate_id, patch_target):
    """A direct inspector that accepts a malformed object must fail closed."""
    def test(self):
        valid_run = execute_scenario(scenario_catalog()[0])
        forged = NamedOracleEvidence(
            "ORACLE-" + predicate_id,
            False,
            (),
            "E26-FORGED-NONDETECTION",
        )
        with patch(patch_target, return_value=forged):
            with self.assertRaisesRegex(
                AssertionError,
                "E25_NAMED_ORACLE_MISSED_CONTROLLED_VIOLATION:" + predicate_id,
            ):
                execute_controlled_violation(predicate_id, valid_run)
    return test


for _predicate_id in sorted(invariant_registry()):
    setattr(
        EvaluationV2Tests,
        "test_controlled_violation_" + _predicate_id.lower(),
        _make_controlled_violation_test(_predicate_id),
    )


for _predicate_id, _patch_target in (
    ("HAS_EPISODE", "invariant_registry._inspect_missing_episode"),
    ("NONEMPTY_EVENTS", "invariant_registry._inspect_empty_run_events"),
    ("STEP_MONOTONIC", "invariant_registry._inspect_nonmonotonic_step_boundary"),
):
    setattr(
        EvaluationV2Tests,
        "test_direct_oracle_tampering_fails_closed_" + _predicate_id.lower(),
        _make_direct_oracle_tamper_test(_predicate_id, _patch_target),
    )


if __name__ == "__main__":
    unittest.main()
