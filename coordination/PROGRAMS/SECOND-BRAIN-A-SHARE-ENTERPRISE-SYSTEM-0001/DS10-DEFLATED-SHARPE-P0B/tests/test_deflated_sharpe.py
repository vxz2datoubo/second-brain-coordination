from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "offline_research"))
import deflated_sharpe as dsr  # noqa: E402


FIXTURE = json.loads((ROOT / "fixtures" / "bailey_lopez_de_prado_2014_formula_reference.json").read_text(encoding="utf-8"))


def canonical_chain():
    """Build only an in-memory view of the already canonical P0A/W4 evidence."""
    binding = dsr._load_verified_w4_binding_module()
    handle = binding.resolve_canonical_w4_store_v1()
    auth = binding.ReadAuthorization(binding.GOVERNED_TASK_ID, binding.GOVERNED_ROUTE_EPOCH,
                                    binding.GOVERNED_EXECUTOR_ROLE, binding.GOVERNED_WORK_CLAIM_REF,
                                    binding.GOVERNED_AUTH_WITNESS_REF)
    _, receipt = binding.read_canonical_family(handle.family_id, handle.family_revision_id,
                                               authorization=auth, observed_at="2026-09-10T00:00:00Z")
    audit = {
        "schema": "ResearchIntegrityAudit/v1", "audit_version": "P0A",
        "experiment_family_ref": receipt["experiment_family_ref"],
        "research_integrity_disposition": "ELIGIBLE_FOR_W7_VALIDATION",
        "w4_authority_state": "CANONICAL_W4_BINDING_VERIFIED",
        "w7_handoff_is_acceptance": False,
        "trial_reconciliation": {"observed_trial_count": receipt["trial_count"]},
    }
    p0a = dsr._load_verified_p0a_module()
    audit["audit_digest"] = p0a.canonical_audit_digest(audit)
    return receipt, audit


def valid_inputs():
    receipt, audit = canonical_chain()
    observation = dsr.ObservedSharpeEvidence(1.2, 1250, "DAILY", "NATIVE_HORIZON", "returns:fixture-v1",
                                              "GROSS", None, receipt["selected_trial_id"])
    moments = dsr.SharpeSamplingMoments(0.0, 3.0, dsr.KurtosisSemantics.PEARSON)
    trials = dsr.IndependentTrialEstimate(
        receipt["experiment_family_ref"], receipt["family_revision_id"], receipt["family_content_digest"],
        receipt["selected_trial_id"], receipt["trial_count"], 2.0, "dependence:fixture-v1", "dependence:fixture-v1",
        0.25, audit, receipt)
    return observation, moments, trials


class AnalyticAndReferenceTests(unittest.TestCase):
    def test_01_paper_formula_reference_fixture(self):
        item = FIXTURE["input"]
        trial = dsr.IndependentTrialEstimate("f@r", "r", "0" * 64, "t", 100, item["effective_trial_count"],
                                              "m", "d", item["sharpe_cross_section_variance"], None, None)
        benchmark = dsr.expected_max_sharpe_benchmark(trial)
        obs = dsr.ObservedSharpeEvidence(item["observed_sharpe"], item["sample_count"], "DAILY", "NATIVE_HORIZON",
                                          "returns:fixture", "GROSS", None, "t")
        psr = dsr.probabilistic_sharpe_ratio(obs, dsr.SharpeSamplingMoments(item["skewness"], item["pearson_kurtosis"], dsr.KurtosisSemantics.PEARSON), benchmark)
        for actual, expected in ((benchmark.quantile_one, FIXTURE["expected"]["quantile_one"]),
                                 (benchmark.quantile_two, FIXTURE["expected"]["quantile_two"]),
                                 (benchmark.expected_max_sharpe, FIXTURE["expected"]["expected_max_sharpe"]),
                                 (psr.z_score, FIXTURE["expected"]["psr_z_score"]),
                                 (psr.probability, FIXTURE["expected"]["deflated_sharpe_probability"])):
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12))

    def test_02_excess_and_pearson_convert_to_one_canonical_convention(self):
        observation, pearson, trials = valid_inputs()
        excess = dsr.SharpeSamplingMoments(pearson.sample_skewness, 0.0, dsr.KurtosisSemantics.EXCESS)
        self.assertAlmostEqual(dsr.compute_deflated_sharpe(observation, pearson, trials).deflated_sharpe_probability,
                               dsr.compute_deflated_sharpe(observation, excess, trials).deflated_sharpe_probability, places=14)

    def test_03_higher_effective_trial_count_raises_expected_max(self):
        _, _, trials = valid_inputs()
        low = dsr.expected_max_sharpe_benchmark(replace(trials, effective_trial_count=2.0))
        high = dsr.expected_max_sharpe_benchmark(replace(trials, effective_trial_count=3.0))
        self.assertGreater(high.expected_max_sharpe, low.expected_max_sharpe)

    def test_04_non_normality_penalty_changes_psr_in_expected_direction(self):
        observation, _, trials = valid_inputs()
        observation = replace(observation, sample_count=5)
        normal = dsr.compute_deflated_sharpe(observation, dsr.SharpeSamplingMoments(0.0, 3.0, dsr.KurtosisSemantics.PEARSON), trials)
        fat_tail = dsr.compute_deflated_sharpe(observation, dsr.SharpeSamplingMoments(0.0, 9.0, dsr.KurtosisSemantics.PEARSON), trials)
        self.assertLess(fat_tail.deflated_sharpe_probability, normal.deflated_sharpe_probability)

    def test_05_single_independent_trial_is_not_selection_test(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(observation, moments, replace(trials, effective_trial_count=1.0))
        self.assertEqual(result.method_state, dsr.MethodState.NOT_APPLICABLE_SINGLE_TRIAL.value)
        self.assertIsNone(result.deflated_sharpe_probability)


class TrialLaunderingTests(unittest.TestCase):
    def test_06_caller_trial_count_cannot_replace_receipt_count(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(observation, moments, replace(trials, raw_trial_count=10))
        self.assertEqual(result.method_state, dsr.MethodState.INPUT_INTEGRITY_BLOCKED.value)
        self.assertIsNone(result.deflated_sharpe_probability)

    def test_07_effective_count_above_raw_is_invalid(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(observation, moments, replace(trials, effective_trial_count=4.0))
        self.assertEqual(result.method_state, dsr.MethodState.INPUT_INTEGRITY_BLOCKED.value)

    def test_08_unresolved_dependence_abstains(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(observation, moments, replace(trials, dependence_resolved=False, dependence_evidence_ref=None))
        self.assertEqual(result.method_state, dsr.MethodState.EFFECTIVE_TRIAL_COUNT_UNRESOLVED.value)
        self.assertIsNone(result.deflated_sharpe_probability)

    def test_09_stale_family_identity_reuse_is_rejected(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(observation, moments, replace(trials, family_content_digest="f" * 64))
        self.assertEqual(result.input_integrity_state, dsr.InputIntegrityState.INPUT_INTEGRITY_BLOCKED.value)

    def test_10_selected_trial_must_be_canonical_selected_trial(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(replace(observation, selected_trial_id="laundered-winner"), moments, trials)
        self.assertEqual(result.method_state, dsr.MethodState.INPUT_INTEGRITY_BLOCKED.value)


class NumericalGuardTests(unittest.TestCase):
    def test_11_nan_and_infinity_never_emit_probability(self):
        observation, moments, trials = valid_inputs()
        for value in (math.nan, math.inf):
            result = dsr.compute_deflated_sharpe(replace(observation, observed_sharpe=value), moments, trials)
            self.assertEqual(result.method_state, dsr.MethodState.ABSTAIN.value)
            self.assertIsNone(result.deflated_sharpe_probability)

    def test_12_impossible_kurtosis_is_moments_invalid(self):
        observation, _, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(observation, dsr.SharpeSamplingMoments(0.0, 0.9, dsr.KurtosisSemantics.PEARSON), trials)
        self.assertEqual(result.method_state, dsr.MethodState.MOMENTS_INVALID.value)

    def test_13_non_positive_psr_denominator_fails_closed(self):
        observation, _, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(replace(observation, observed_sharpe=1.0),
                                             dsr.SharpeSamplingMoments(2.0, 1.0, dsr.KurtosisSemantics.PEARSON), trials)
        self.assertEqual(result.method_state, dsr.MethodState.NUMERICAL_FAILURE.value)
        self.assertIsNone(result.deflated_sharpe_probability)

    def test_14_extreme_values_do_not_silently_overflow(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(replace(observation, observed_sharpe=1e308), moments,
                                             replace(trials, sharpe_cross_section_variance=1e308))
        self.assertIn(result.method_state, {dsr.MethodState.NUMERICAL_FAILURE.value, dsr.MethodState.ABSTAIN.value})
        self.assertIsNone(result.deflated_sharpe_probability)

    def test_15_precision_and_annualization_guards_abstain(self):
        observation, moments, trials = valid_inputs()
        for changed in (replace(observation, source_precision="DISPLAY_ROUNDED"), replace(observation, annualization_policy="UNKNOWN")):
            self.assertEqual(dsr.compute_deflated_sharpe(changed, moments, trials).method_state, dsr.MethodState.ABSTAIN.value)

    def test_16_net_metric_requires_cost_model_identity(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(replace(observation, net_or_gross_metric="NET", cost_model_ref=None), moments, trials)
        self.assertEqual(result.method_state, dsr.MethodState.ABSTAIN.value)


class AuthorityAndContractTests(unittest.TestCase):
    def test_17_noncanonical_p0a_disposition_cannot_get_p_value(self):
        observation, moments, trials = valid_inputs()
        forged = dict(trials.p0a_audit); forged["research_integrity_disposition"] = "ABSTAIN"
        p0a = dsr._load_verified_p0a_module(); forged["audit_digest"] = p0a.canonical_audit_digest({key: value for key, value in forged.items() if key != "audit_digest"})
        result = dsr.compute_deflated_sharpe(observation, moments, replace(trials, p0a_audit=forged))
        self.assertEqual(result.method_state, dsr.MethodState.INPUT_INTEGRITY_BLOCKED.value)
        self.assertIsNone(result.deflated_sharpe_probability)

    def test_18_result_contract_has_no_w7_or_trade_authority_and_exact_fields(self):
        observation, moments, trials = valid_inputs()
        result = dsr.compute_deflated_sharpe(observation, moments, trials)
        fields = set(result.to_dict())
        expected = {"result_id", "method_id", "method_version", "experiment_family_ref", "family_revision", "family_content_digest", "selected_trial_id", "observed_sharpe", "sample_count", "skewness", "kurtosis", "raw_trial_count", "effective_trial_count", "trial_count_method_ref", "sharpe_cross_section_variance", "expected_max_sharpe_benchmark", "probabilistic_sharpe_against_benchmark", "deflated_sharpe_probability", "numerical_diagnostics", "input_integrity_state", "method_state", "uncertainties", "computation_digest"}
        self.assertEqual(fields, expected)
        self.assertEqual(result.method_state, dsr.MethodState.PASS_COMPUTED.value)
        self.assertNotIn("w7", json.dumps(result.to_dict()).lower())
        self.assertNotIn("trade", json.dumps(result.to_dict()).lower())


if __name__ == "__main__":
    unittest.main()
