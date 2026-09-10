from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "offline_research"))
import pbo_cscv as pbo  # noqa: E402

try:
    import jsonschema
except ImportError:  # pragma: no cover - local optional validation dependency
    jsonschema = None


FIXTURE = json.loads((ROOT / "fixtures" / "pbo-cscv.synthetic.json").read_text(encoding="utf-8"))


def canonical_chain():
    binding = pbo._load_w4_binding()
    handle = binding.resolve_canonical_w4_store_v1()
    auth = binding.ReadAuthorization(
        binding.GOVERNED_TASK_ID, binding.GOVERNED_ROUTE_EPOCH, binding.GOVERNED_EXECUTOR_ROLE,
        binding.GOVERNED_WORK_CLAIM_REF, binding.GOVERNED_AUTH_WITNESS_REF,
    )
    snapshot, receipt = binding.read_canonical_family(
        handle.family_id, handle.family_revision_id, authorization=auth, observed_at="2026-09-10T00:00:00Z"
    )
    audit = {
        "schema": "ResearchIntegrityAudit/v1", "audit_version": "P0A", "audit_id": "ds10-p0a-p0c-synthetic-chain",
        "experiment_family_ref": receipt["experiment_family_ref"],
        "w4_snapshot_digest": receipt["family_content_digest"],
        "research_integrity_disposition": "ELIGIBLE_FOR_W7_VALIDATION",
        "w4_authority_state": "CANONICAL_W4_BINDING_VERIFIED",
        "w7_handoff_is_acceptance": False,
        "trial_reconciliation": {"observed_trial_count": receipt["trial_count"]},
        "pit_evidence": {"authority_binding": {
            "authority_source_ref": "W2-PIT-RULES-SYNTHETIC-V1",
            "rule_snapshot_id": "RULE-SNAPSHOT-SYNTHETIC-V1",
            "dataset_artifact_ref": "DATASET-SNAPSHOT-SYNTHETIC-V1",
        }},
        "authority": {
            "experiment_registry_write_authority": False,
            "strategy_experiment_write_authority": False,
            "probability_authority": False,
            "final_validation_authority": False,
            "risk_override_authority": False,
            "position_authority": False,
            "order_authority": False,
            "trade_authority": False,
        },
    }
    audit["audit_digest"] = pbo._load_p0a().canonical_audit_digest(audit)
    trial_ids = tuple(sorted(item["trial_id"] for item in snapshot["trials"] if item["selection_affecting"] is True))
    return receipt, audit, trial_ids


def valid_input(**changes):
    receipt, audit, trial_ids = canonical_chain()
    case = FIXTURE["complete_synchronous_matrix"]
    value = pbo.CSCVInput(
        w4_read_receipt=receipt,
        p0a_audit=audit,
        trial_ids=trial_ids,
        observation_ids=tuple(case["observation_ids"]),
        performance_matrix=tuple(tuple(row) for row in case["performance_matrix"]),
        performance_measure_id=case["performance_measure_id"],
        performance_measure_version=case["performance_measure_version"],
        higher_is_better=True,
        group_count=4,
        max_combinations=6,
        performance_evidence_refs=("public-safe:synthetic-pbo-cscv-fixture-v1",),
        cost_semantics="SYNTHETIC_NET_OF_DECLARED_COSTS",
        family_revision_ref=receipt["experiment_family_ref"],
        family_revision_digest=receipt["family_content_digest"],
        canonical_read_receipt_ref=f"CanonicalExperimentFamilyReadReceipt/v1:{receipt['receipt_digest']}",
        canonical_read_receipt_digest=receipt["receipt_digest"],
        integrity_audit_ref=f"ResearchIntegrityAudit/v1:{audit['audit_id']}",
        integrity_audit_digest=audit["audit_digest"],
        observation_axis_id="PUBLIC_SAFE_SYNTHETIC_TIME_AXIS_V1",
        observation_time_index_digest=pbo._digest(list(case["observation_ids"])),
        performance_matrix_digest=pbo._digest(case["performance_matrix"]),
        tie_policy=pbo.TIE_POLICY,
        missingness_policy=pbo.MISSINGNESS_POLICY,
        gross_net_semantics=pbo.GROSS_NET_SEMANTICS,
        pit_evidence_ref=audit["pit_evidence"]["authority_binding"]["authority_source_ref"],
        rule_snapshot_ref=audit["pit_evidence"]["authority_binding"]["rule_snapshot_id"],
        data_snapshot_ref=audit["pit_evidence"]["authority_binding"]["dataset_artifact_ref"],
        method_id=pbo.METHOD_ID,
        method_version=pbo.METHOD_VERSION,
        method_code_digest=pbo._code_digest(),
    )
    # Test cases that intentionally substitute a complete finite matrix must
    # rebind its governed digest; malformed/NaN cases deliberately do not.
    final_observations = changes.get("observation_ids", value.observation_ids)
    if "observation_ids" in changes and "observation_time_index_digest" not in changes:
        changes["observation_time_index_digest"] = pbo._digest(list(final_observations))
    final_matrix = changes.get("performance_matrix", value.performance_matrix)
    if "performance_matrix" in changes and "performance_matrix_digest" not in changes:
        try:
            changes["performance_matrix_digest"] = pbo._digest([list(row) for row in final_matrix])
        except ValueError:  # NaN / Inf is independently rejected before digest use.
            pass
    return replace(value, **changes)


def input_payload(value):
    return {
        "schema": "CSCVInput/v1", "w4_read_receipt": dict(value.w4_read_receipt), "p0a_audit": dict(value.p0a_audit),
        "trial_ids": list(value.trial_ids), "observation_ids": list(value.observation_ids),
        "performance_matrix": [list(row) for row in value.performance_matrix],
        "performance_measure_id": value.performance_measure_id, "performance_measure_version": value.performance_measure_version,
        "higher_is_better": value.higher_is_better, "group_count": value.group_count, "max_combinations": value.max_combinations,
        "performance_evidence_refs": list(value.performance_evidence_refs), "cost_semantics": value.cost_semantics,
        "family_revision_ref": value.family_revision_ref, "family_revision_digest": value.family_revision_digest,
        "canonical_read_receipt_ref": value.canonical_read_receipt_ref, "canonical_read_receipt_digest": value.canonical_read_receipt_digest,
        "integrity_audit_ref": value.integrity_audit_ref, "integrity_audit_digest": value.integrity_audit_digest,
        "observation_axis_id": value.observation_axis_id, "observation_time_index_digest": value.observation_time_index_digest,
        "performance_matrix_digest": value.performance_matrix_digest, "tie_policy": value.tie_policy,
        "missingness_policy": value.missingness_policy, "gross_net_semantics": value.gross_net_semantics,
        "pit_evidence_ref": value.pit_evidence_ref, "rule_snapshot_ref": value.rule_snapshot_ref,
        "data_snapshot_ref": value.data_snapshot_ref, "method_id": value.method_id,
        "method_version": value.method_version, "method_code_digest": value.method_code_digest,
        "ordering_policy": value.ordering_policy, "combination_policy": value.combination_policy,
    }


class ExactCSCVContractTests(unittest.TestCase):
    def test_s4_enumerates_all_six_oriented_halves(self):
        result = pbo.compute_pbo_cscv(valid_input())
        self.assertEqual(result.applicability_state, pbo.ComputationState.PASS_COMPUTED.value)
        self.assertEqual(result.combination_count, 6)
        self.assertEqual(result.evaluated_split_count, 6)
        seen = {(item.is_group_ids, item.oos_group_ids) for item in result.split_results}
        self.assertEqual(len(seen), 6)
        self.assertIn(((0, 1), (2, 3)), seen)
        self.assertIn(((2, 3), (0, 1)), seen)  # complements remain oriented, never divided by two

    def test_s16_exact_count_is_12870_not_paper_prose_typo(self):
        result = pbo.compute_pbo_cscv(valid_input(
            observation_ids=tuple(f"t{i:02d}" for i in range(16)),
            performance_matrix=tuple((float(i + 1), float(100 - i), float(50 + i * 0.1)) for i in range(16)),
            group_count=16,
            max_combinations=12869,
        ))
        self.assertEqual(result.applicability_state, pbo.ComputationState.COMBINATORIAL_BUDGET_EXCEEDED.value)
        self.assertEqual(result.combination_count, 12870)
        self.assertIsNone(result.pbo_estimate)

    def test_budget_exceeded_abstains_without_sampling_or_early_stop(self):
        result = pbo.compute_pbo_cscv(valid_input(max_combinations=5))
        self.assertEqual(result.applicability_state, pbo.ComputationState.COMBINATORIAL_BUDGET_EXCEEDED.value)
        self.assertEqual(result.evaluated_split_count, 0)
        self.assertIn("EXACT_ENUMERATION_REQUIRED_NO_SAMPLING", result.uncertainties)

    def test_best_is_selected_once_then_ranked_oos_worst_to_best(self):
        result = pbo.compute_pbo_cscv(valid_input())
        first = result.split_results[0]
        self.assertEqual(first.is_group_ids, (0, 1))
        self.assertEqual(first.selected_trial_id, "t3")
        self.assertEqual(first.oos_rank, 3)
        self.assertEqual(first.omega, 0.75)
        self.assertGreater(first.logit, 0.0)
        self.assertFalse(first.median_mass)
        self.assertFalse(first.split_overfit)

    def test_zero_logit_is_tracked_as_median_mass_not_overfit(self):
        matrix = ((72.0, 60.0, 98.0), (23.0, 39.0, 72.0),
                  (35.0, 68.0, 29.0), (4.0, 40.0, 20.0))
        result = pbo.compute_pbo_cscv(valid_input(performance_matrix=matrix))
        self.assertEqual(result.applicability_state, pbo.ComputationState.PASS_COMPUTED.value)
        self.assertEqual(result.median_mass_count, 6)
        self.assertEqual(result.pbo_estimate, 0.0)
        self.assertTrue(all(item.logit == 0.0 and not item.split_overfit for item in result.split_results))

    def test_logit_uses_unclipped_rank_fraction_and_pbo_uses_strict_negative(self):
        result = pbo.compute_pbo_cscv(valid_input())
        for split in result.split_results:
            self.assertEqual(split.omega, split.oos_rank / 4.0)
            self.assertTrue(math.isclose(split.logit, math.log(split.omega / (1.0 - split.omega)), abs_tol=1e-15))
            self.assertEqual(split.split_overfit, split.logit < 0.0)
        self.assertEqual(result.pbo_estimate, sum(item.split_overfit for item in result.split_results) / 6.0)

    def test_repeatability_and_canonical_combination_order(self):
        first = pbo.compute_pbo_cscv(valid_input())
        second = pbo.compute_pbo_cscv(valid_input())
        self.assertEqual(first.computation_digest, second.computation_digest)
        self.assertEqual([item.is_group_ids for item in first.split_results],
                         [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])

    def test_result_evidence_binds_complete_ordered_split_ledger(self):
        result = pbo.compute_pbo_cscv(valid_input())
        self.assertEqual(result.pbo_numerator, sum(item.split_overfit for item in result.split_results))
        self.assertEqual(result.pbo_denominator, result.evaluated_split_count)
        self.assertEqual(result.ordered_split_ledger_digest,
                         pbo._digest([item.to_dict() for item in result.split_results]))
        self.assertEqual(result.logit_distribution_digest, pbo._digest([item.logit for item in result.split_results]))
        self.assertEqual(result.combination_manifest_digest, pbo._digest([
            {"split_id": item.split_id, "is_group_ids": list(item.is_group_ids), "oos_group_ids": list(item.oos_group_ids)}
            for item in result.split_results
        ]))
        self.assertTrue(all(item.selected_trial_identity_digest and item.is_score_vector_digest and item.oos_score_vector_digest
                            for item in result.split_results))

    def test_column_permutation_with_identity_restoration_is_invariant(self):
        source = valid_input()
        order = (2, 0, 1)
        shuffled_ids = tuple(source.trial_ids[index] for index in order)
        shuffled_rows = tuple(tuple(row[index] for index in order) for row in source.performance_matrix)
        restored = sorted(zip(shuffled_ids, range(len(shuffled_ids))))
        rebuilt_ids = tuple(item[0] for item in restored)
        rebuilt_rows = tuple(tuple(row[index] for _, index in restored) for row in shuffled_rows)
        result = pbo.compute_pbo_cscv(replace(source, trial_ids=rebuilt_ids, performance_matrix=rebuilt_rows))
        self.assertEqual(result.computation_digest, pbo.compute_pbo_cscv(source).computation_digest)


class GuardAndAdversarialTests(unittest.TestCase):
    def test_odd_s_and_nondivisible_t_are_invalid_partition_design(self):
        self.assertEqual(pbo.compute_pbo_cscv(valid_input(group_count=3)).applicability_state,
                         pbo.ComputationState.INVALID_PARTITION_DESIGN.value)
        self.assertEqual(pbo.compute_pbo_cscv(valid_input(group_count=2, observation_ids=("a", "b", "c"),
                                                       performance_matrix=((1.0, 2.0, 3.0),) * 3)).applicability_state,
                         pbo.ComputationState.INVALID_PARTITION_DESIGN.value)

    def test_material_is_tie_abstains_without_lexical_fallback(self):
        source = valid_input()
        tied = tuple((1.0, 1.0, float(index + 3)) for index in range(4))
        result = pbo.compute_pbo_cscv(valid_input(performance_matrix=tied))
        self.assertEqual(result.applicability_state, pbo.ComputationState.ABSTAIN.value)
        self.assertIn("RANK_TIE_UNRESOLVED", result.uncertainties)
        self.assertEqual(result.evaluated_split_count, 0)

    def test_oos_tie_also_abstains(self):
        source = valid_input()
        matrix = ((9.0, 1.0, 5.0), (8.0, 2.0, 6.0), (1.0, 9.0, 5.0), (2.0, 8.0, 6.0))
        result = pbo.compute_pbo_cscv(valid_input(performance_matrix=matrix))
        self.assertEqual(result.applicability_state, pbo.ComputationState.ABSTAIN.value)
        self.assertIn("RANK_TIE_UNRESOLVED", result.uncertainties)

    def test_nonfinite_or_incomplete_matrix_never_shrinks_family(self):
        source = valid_input()
        nonfinite = list(source.performance_matrix); nonfinite[0] = (math.nan, 2.0, 3.0)
        self.assertEqual(pbo.compute_pbo_cscv(replace(source, performance_matrix=tuple(nonfinite))).applicability_state,
                         pbo.ComputationState.MISSINGNESS_UNRESOLVED.value)
        self.assertEqual(pbo.compute_pbo_cscv(replace(source, performance_matrix=source.performance_matrix[:-1])).applicability_state,
                         pbo.ComputationState.MISSINGNESS_UNRESOLVED.value)

    def test_winner_list_laundering_or_family_deletion_is_blocked(self):
        source = valid_input()
        reduced = replace(source, trial_ids=source.trial_ids[:-1],
                          performance_matrix=tuple(row[:-1] for row in source.performance_matrix))
        result = pbo.compute_pbo_cscv(reduced)
        self.assertEqual(result.applicability_state, pbo.ComputationState.INPUT_INTEGRITY_BLOCKED.value)
        self.assertIn("FAMILY_MATRIX_INCOMPLETE_OR_CHAIN_MISMATCH", result.uncertainties)

    def test_p0a_audit_tampering_is_blocked(self):
        source = valid_input()
        bad = dict(source.p0a_audit); bad["research_integrity_disposition"] = "ACCEPT"
        result = pbo.compute_pbo_cscv(replace(source, p0a_audit=bad))
        self.assertEqual(result.applicability_state, pbo.ComputationState.INPUT_INTEGRITY_BLOCKED.value)

    def test_metric_evidence_and_ordering_laundering_abstain(self):
        source = valid_input()
        self.assertEqual(pbo.compute_pbo_cscv(replace(source, performance_evidence_refs=())).applicability_state,
                         pbo.ComputationState.ABSTAIN.value)
        self.assertEqual(pbo.compute_pbo_cscv(replace(source, ordering_policy="CALLER_ORDER")).applicability_state,
                         pbo.ComputationState.ABSTAIN.value)

    def test_metric_relabel_cannot_reuse_arithmetic_mean_scorer(self):
        source = valid_input()
        for relabel in ("SHARPE_RATIO", "SORTINO_RATIO", "CALMAR_RATIO"):
            result = pbo.compute_pbo_cscv(replace(source, performance_measure_id=relabel))
            self.assertNotEqual(result.applicability_state, pbo.ComputationState.PASS_COMPUTED.value)
            self.assertEqual(result.applicability_state, pbo.ComputationState.INPUT_INTEGRITY_BLOCKED.value)
        unsupported_version = pbo.compute_pbo_cscv(replace(source, performance_measure_version="2.0.0"))
        self.assertEqual(unsupported_version.applicability_state, pbo.ComputationState.ABSTAIN.value)
        self.assertIn("PERFORMANCE_MEASURE_UNSUPPORTED_OR_UNRESOLVED", unsupported_version.uncertainties)

    def test_missing_or_mismatched_provenance_never_passes(self):
        source = valid_input()
        result = pbo.compute_pbo_cscv(replace(source, performance_matrix_digest="0" * 64))
        self.assertEqual(result.applicability_state, pbo.ComputationState.INPUT_INTEGRITY_BLOCKED.value)
        result = pbo.compute_pbo_cscv(replace(source, pit_evidence_ref="UNRESOLVED"))
        self.assertEqual(result.applicability_state, pbo.ComputationState.INPUT_INTEGRITY_BLOCKED.value)

    def test_result_has_no_validation_probability_or_trade_authority(self):
        result = pbo.compute_pbo_cscv(valid_input()).to_dict()
        self.assertEqual(result["applicability_state"], "PASS_COMPUTED")
        self.assertNotIn("probability", result)
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertFalse(result["authority"]["pbo_result_is_w7_accept"])


@unittest.skipUnless(jsonschema is not None, "jsonschema not installed")
class SchemaTests(unittest.TestCase):
    def test_input_and_split_validate_closed_schemas(self):
        input_schema = json.loads((ROOT / "CSCV-INPUT.schema.json").read_text(encoding="utf-8"))
        split_schema = json.loads((ROOT / "CSCV-SPLIT-RESULT.schema.json").read_text(encoding="utf-8"))
        source = valid_input(); result = pbo.compute_pbo_cscv(source)
        jsonschema.Draft202012Validator(input_schema).validate(input_payload(source))
        jsonschema.Draft202012Validator(split_schema).validate(result.split_results[0].to_dict())

    def test_pass_result_validates_closed_schema(self):
        schema = json.loads((ROOT / "PBO-RESULT.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(pbo.compute_pbo_cscv(valid_input()).to_dict())

    def test_schema_rejects_trade_authority_or_unknown_field(self):
        schema = json.loads((ROOT / "PBO-RESULT.schema.json").read_text(encoding="utf-8"))
        payload = pbo.compute_pbo_cscv(valid_input()).to_dict()
        payload["authority"]["trade_authority"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(payload)
        payload = pbo.compute_pbo_cscv(valid_input()).to_dict(); payload["caller_winner_ledger"] = {}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(payload)


if __name__ == "__main__":
    unittest.main()
