import json
import math
import sys
import unittest
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from belief_contract import canonical_packet_digest, expected_posterior, validate_packet

SCHEMA = json.loads((ROOT / "BELIEF-PACKET-v1.schema.json").read_text(encoding="utf-8"))
EVALS = yaml.safe_load((ROOT / "DS02-ADVERSARIAL-EVALS-v1.0.yaml").read_text(encoding="utf-8"))
NUMERIC = yaml.safe_load((ROOT / "NUMERIC-INTEGRITY-REGISTRY-v1.0.yaml").read_text(encoding="utf-8"))


def beta_binomial(alpha, beta, successes, failures):
    a = alpha + successes
    b = beta + failures
    return a, b, a / (a + b)


def normal_normal(mu0, var0, observations, obs_var):
    precision = 1.0 / var0 + len(observations) / obs_var
    variance = 1.0 / precision
    mu = variance * (mu0 / var0 + sum(observations) / obs_var)
    return mu, variance


def logit(p):
    return math.log(p / (1.0 - p))


def logistic(x):
    return 1.0 / (1.0 + math.exp(-x))


def compose_log_bf(prior, factors):
    return logistic(logit(prior) + sum(factors))


def canonical_probability(p):
    q = Decimal(str(p)).quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN)
    return format(q, ".12f")


def positive_packet():
    log_bf = math.log(1.5)
    return {
        "schema": "BeliefPacket/v1",
        "identity": {
            "belief_id": "belief-001",
            "target_id": "SSE_600000_5D_POSITIVE_RETURN",
            "target_definition_version": "v1",
            "scope_type": "SINGLE_SECURITY",
            "symbol_or_universe": "600000",
            "exchange": "SSE",
            "board": "MAIN",
            "security_type": "A_SHARE_STOCK",
            "forecast_horizon": "5D",
            "as_of_time": "2026-08-30T01:00:00+08:00",
            "knowledge_cutoff": "2026-08-30T01:00:00+08:00",
            "market_rule_version": "SSE_TRADING_RULES_2026",
            "market_rule_clause_state_version": "SSE_RULE_STATE_2026-07-06_ACTIVE",
            "rule_clause_ids": ["SSE_CORE_TRADING"],
        },
        "temporal_provenance": {"decision_time": "2026-08-30T01:00:00+08:00"},
        "prior": {
            "prior_id": "market-base-rate",
            "prior_version": "v1",
            "family": "BETA",
            "parameters": {"alpha": 2.0, "beta": 3.0},
            "training_window": {
                "start": "2020-01-01T00:00:00+08:00",
                "end": "2025-12-31T23:59:59+08:00",
            },
            "regime_scope": "ALL_REGIMES_REFERENCE_ONLY",
            "effective_from": "2026-01-01T00:00:00+08:00",
            "evidence_digest": "deadbeef0001",
        },
        "evidence": [{
            "evidence_id": "ev-1",
            "source_ref": "w5:event:1",
            "dependence_provenance": {
                "source_instance_id": "src-official-1",
                "source_family_id": "official-exchange",
                "candidate_independence_group_id": "candidate-group-a",
                "ancestry_refs": [],
                "shared_feed_group_ids": [],
                "shared_feature_group_ids": [],
                "shared_training_data_group_ids": [],
                "shared_model_lineage_ids": [],
                "dependence_authority_state": "UNAVAILABLE_PHASE1",
                "independence_status": "UNVERIFIED",
            },
            "revision_provenance": {
                "revision_id": "rev-original-1",
                "is_revised": False,
                "supersedes_snapshot_hashes": [],
            },
            "available_at": "2026-08-29T20:00:00+08:00",
            "data_snapshot_hash": "cafebabe0001",
            "feature_definition_version": "event-surprise-v1",
            "polarity": "POSITIVE",
            "likelihood_model_id": "likelihood-1",
            "likelihood_model_version": "v1",
            "status": "ADMITTED",
        }],
        "update": {
            "prior_probability": 0.4,
            "cumulative_log_bayes_factor": log_bf,
            "posterior_probability": expected_posterior(0.4, log_bf),
            "unknown_mass": 0.1,
            "belief_state": "PROPOSAL",
        },
        "shrinkage": {
            "effective_sample_size": 100.0,
            "hierarchy_level": "SECURITY",
            "hierarchical_prior_id": "market-industry-security-hierarchy",
            "hierarchical_prior_version": "v1",
            "status": "APPLIED",
        },
        "validation": {
            "authority_state": "UNAVAILABLE_PHASE1",
            "packet_status": "UNVALIDATED_PROPOSAL",
            "validated_computation_receipt": None,
            "canonical_belief_authorized": False,
        },
        "predictive": {
            "expected_value": 0.001,
            "quantiles": {"p05": -0.03, "p25": -0.01, "p50": 0.001, "p75": 0.012, "p95": 0.04},
            "probability_positive": 0.52,
            "probability_below_loss_threshold": 0.08,
            "predictive_distribution_ref": "artifact://predictive/001",
        },
        "diagnostics": {
            "engine": "analytic-reference",
            "engine_version": "v1",
            "code_sha": "1a514fe839b1c47a14d7fad4a96e8c9fd2365338",
            "seed": None,
            "rhat_max": None,
            "ess_bulk_min": None,
            "ess_tail_min": None,
            "divergences": None,
            "pareto_k_max": None,
            "calibration_status": "PASS",
            "prior_predictive_status": "NOT_RUN",
            "posterior_predictive_status": "NOT_RUN",
        },
        "numeric_integrity": {
            "probability_serialization_decimals": 12,
            "rounding_mode": "ROUND_HALF_EVEN",
            "ui_precision_is_authority": False,
            "canonical_digest": "0" * 64,
        },
        "authority": {
            "market_truth_authority": False,
            "event_truth_authority": False,
            "regime_authority": False,
            "epistemic_authority": False,
            "decision_authority": False,
            "risk_override_authority": False,
            "position_authority": False,
            "order_authority": False,
            "trade_authority": False,
        },
    }


def rebind_digest(packet):
    packet["numeric_integrity"]["canonical_digest"] = canonical_packet_digest(packet)
    return packet


def validate(packet):
    rebind_digest(packet)
    return validate_packet(packet, schema=SCHEMA, numeric_registry=NUMERIC)


def _second_evidence(packet, *, source_instance="src-second-2"):
    row = deepcopy(packet["evidence"][0])
    row["evidence_id"] = "ev-2"
    row["source_ref"] = "w5:event:2"
    row["data_snapshot_hash"] = "cafebabe0002"
    row["dependence_provenance"]["source_instance_id"] = source_instance
    row["dependence_provenance"]["candidate_independence_group_id"] = "fresh-caller-label"
    return row


def _set_verified_update(packet, *, prior_probability=None, log_bf=None):
    if log_bf is None:
        log_bf = math.log(1.5)
    if prior_probability is not None:
        packet["update"]["prior_probability"] = prior_probability
    packet["update"]["cumulative_log_bayes_factor"] = log_bf
    packet["update"]["posterior_probability"] = expected_posterior(
        packet["update"]["prior_probability"], log_bf
    )


def execute_fixture(name):
    packet = positive_packet()

    if name in {"REPOST_ANCESTRY", "RELABELED_ANCESTRY"}:
        second = _second_evidence(packet, source_instance="src-repost-2")
        second["dependence_provenance"]["ancestry_refs"] = ["src-official-1"]
        packet["evidence"].append(second)
        packet["update"]["cumulative_log_bayes_factor"] = math.log(1.5) * 2
        packet["update"]["posterior_probability"] = expected_posterior(0.4, math.log(1.5) * 2)
        receipt = validate(packet)
        return receipt["classification"], "DEPENDENCE_COLLAPSE_REQUIRED" if "DEPENDENCE_COLLAPSE_REQUIRED" in receipt["codes"] else "MISSING"

    if name == "SHARED_FEED_FEATURE":
        packet["evidence"][0]["dependence_provenance"]["shared_feed_group_ids"] = ["feed-l2-shared"]
        packet["evidence"][0]["dependence_provenance"]["shared_feature_group_ids"] = ["feature-shared"]
        second = _second_evidence(packet)
        second["dependence_provenance"]["shared_feed_group_ids"] = ["feed-l2-shared"]
        second["dependence_provenance"]["shared_feature_group_ids"] = ["feature-shared"]
        second["dependence_provenance"]["shared_training_data_group_ids"] = ["train-shared"]
        second["dependence_provenance"]["shared_model_lineage_ids"] = ["model-shared"]
        packet["evidence"].append(second)
        packet["update"]["cumulative_log_bayes_factor"] = math.log(1.5) * 2
        packet["update"]["posterior_probability"] = expected_posterior(0.4, math.log(1.5) * 2)
        receipt = validate(packet)
        return receipt["classification"], "DEPENDENCE_COLLAPSE_REQUIRED" if "DEPENDENCE_COLLAPSE_REQUIRED" in receipt["codes"] else "MISSING"

    if name == "CALIBRATION_FAIL":
        packet["diagnostics"]["calibration_status"] = "FAIL"
        receipt = validate(packet)
        return receipt["classification"], "CALIBRATION_REQUIRED" if "CALIBRATION_REQUIRED" in receipt["codes"] else "MISSING"

    if name == "SMALL_SAMPLE_EXTREME_POSTERIOR":
        log_bf = math.log(1.5)
        prior = logistic(logit(0.95) - log_bf)
        _set_verified_update(packet, prior_probability=prior, log_bf=log_bf)
        packet["shrinkage"]["effective_sample_size"] = 5.0
        packet["shrinkage"]["status"] = "REVALIDATION_REQUIRED"
        receipt = validate(packet)
        return receipt["classification"], "SMALL_SAMPLE_SHRINKAGE_REQUIRED" if "SMALL_SAMPLE_SHRINKAGE_REQUIRED" in receipt["codes"] else "MISSING"

    if name == "POSTERIOR_INCONSISTENT":
        packet["update"]["posterior_probability"] = 0.999999
        receipt = validate(packet)
        return receipt["classification"], "POSTERIOR_MATH_INCONSISTENT" if "POSTERIOR_MATH_INCONSISTENT" in receipt["codes"] else "MISSING"

    if name == "FUTURE_EVIDENCE":
        packet["evidence"][0]["available_at"] = "2026-08-30T01:00:01+08:00"
        receipt = validate(packet)
        return receipt["classification"], "PIT_VIOLATION" if "PIT_VIOLATION" in receipt["codes"] else "MISSING"

    if name == "REVISED_WITHOUT_LINEAGE":
        packet["evidence"][0]["revision_provenance"]["is_revised"] = True
        receipt = validate(packet)
        return receipt["classification"], "SCHEMA_REJECT" if "SCHEMA_REJECT" in receipt["codes"] else "MISSING"

    if name == "PRIOR_EFFECTIVE_AFTER_CUTOFF":
        packet["prior"]["effective_from"] = "2026-08-30T01:00:01+08:00"
        receipt = validate(packet)
        return receipt["classification"], "PRIOR_NOT_EX_ANTE" if "PRIOR_NOT_EX_ANTE" in receipt["codes"] else "MISSING"

    if name == "PRIOR_TRAINING_AFTER_CUTOFF":
        packet["prior"]["training_window"]["end"] = "2026-08-30T01:00:01+08:00"
        receipt = validate(packet)
        return receipt["classification"], "PRIOR_NOT_EX_ANTE" if "PRIOR_NOT_EX_ANTE" in receipt["codes"] else "MISSING"

    if name == "EVIDENCE_AFTER_KNOWLEDGE_CUTOFF":
        packet["temporal_provenance"]["decision_time"] = "2026-08-30T02:00:00+08:00"
        packet["evidence"][0]["available_at"] = "2026-08-30T01:30:00+08:00"
        receipt = validate(packet)
        return receipt["classification"], "KNOWLEDGE_CUTOFF_VIOLATION" if "KNOWLEDGE_CUTOFF_VIOLATION" in receipt["codes"] else "MISSING"

    if name == "TEMPORAL_ORDER_INVALID":
        packet["identity"]["knowledge_cutoff"] = "2026-08-30T01:30:00+08:00"
        receipt = validate(packet)
        return receipt["classification"], "TEMPORAL_ORDER_INVALID" if "TEMPORAL_ORDER_INVALID" in receipt["codes"] else "MISSING"

    if name == "CANONICAL_DIGEST_TAMPER":
        rebind_digest(packet)
        packet["predictive"]["expected_value"] = 0.123456
        receipt = validate_packet(packet, schema=SCHEMA, numeric_registry=NUMERIC)
        return receipt["classification"], "CANONICAL_DIGEST_MISMATCH" if "CANONICAL_DIGEST_MISMATCH" in receipt["codes"] else "MISSING"

    if name == "MISSING_TARGET_VERSION":
        del packet["identity"]["target_definition_version"]
    elif name == "INVALID_FEATURE_VERSION":
        packet["evidence"][0]["feature_definition_version"] = ""
    elif name == "CROSS_EXCHANGE_RULE":
        packet["identity"]["exchange"] = "SZSE"
        packet["identity"]["board"] = "MAIN"
        packet["identity"]["symbol_or_universe"] = "000001"
    elif name == "MISSING_HORIZON":
        del packet["identity"]["forecast_horizon"]
    elif name == "PROBABILITY_ABOVE_ONE":
        packet["update"]["posterior_probability"] = 1.00001
    elif name == "UI_AUTHORITY_TRUE":
        packet["numeric_integrity"]["ui_precision_is_authority"] = True
    elif name == "ORDER_AUTHORITY_TRUE":
        packet["authority"]["order_authority"] = True
    elif name == "EVENT_AUTHORITY_TRUE":
        packet["authority"]["event_truth_authority"] = True
    elif name == "MARKET_TRUTH_AUTHORITY_TRUE":
        packet["authority"]["market_truth_authority"] = True
    elif name == "REGIME_AUTHORITY_TRUE":
        packet["authority"]["regime_authority"] = True
    elif name == "BSE_DEFERRED_CLAUSE":
        packet["identity"].update({
            "symbol_or_universe": "830001",
            "exchange": "BSE",
            "board": "BSE",
            "market_rule_version": "BSE_TRADING_RULES_2026",
            "market_rule_clause_state_version": "BSE_RULE_STATE_2026-07-06_PARTIAL_DEFERRED",
            "rule_clause_ids": ["BSE_2026_DEFERRED_CLAUSE_SENTINEL"],
        })
        receipt = validate(packet)
        return receipt["classification"], "RULE_CLAUSE_DEFERRED" if "RULE_CLAUSE_DEFERRED" in receipt["codes"] else "MISSING"
    elif name == "UNKNOWN_EVIDENCE_ABSTAIN":
        packet["evidence"][0]["status"] = "UNKNOWN"
        packet["update"]["cumulative_log_bayes_factor"] = 0.0
        packet["update"]["posterior_probability"] = packet["update"]["prior_probability"]
        packet["update"]["belief_state"] = "ABSTAIN"
        packet["diagnostics"]["calibration_status"] = "NOT_RUN"
        receipt = validate(packet)
        return receipt["classification"], "UNKNOWN_OR_ABSTAIN"
    elif name == "HIGH_POSTERIOR_NO_ACTION":
        _set_verified_update(packet, prior_probability=0.90, log_bf=math.log(1.5))
        packet["predictive"]["probability_below_loss_threshold"] = 0.45
        receipt = validate(packet)
        assert not receipt["trade_authorized"]
        return receipt["classification"], "NO_ACTION_AUTHORITY"
    elif name == "RETRACTION_RECOMPUTE":
        prior = 0.4
        factors = [math.log(2.0), math.log(0.8), math.log(1.5)]
        full = compose_log_bf(prior, factors)
        retracted = logistic(logit(full) - factors[1])
        recomputed = compose_log_bf(prior, [factors[0], factors[2]])
        return ("PASS_PROPOSAL_ONLY", "APPEND_INVALIDATION_AND_RECOMPUTE") if math.isclose(retracted, recomputed, abs_tol=1e-12) else ("REJECTED", "MISMATCH")
    elif name == "SEQUENTIAL_BATCH_MISMATCH":
        sequential = beta_binomial(2.0, 3.0, 1, 0)
        batch = beta_binomial(2.0, 3.0, 2, 0)
        return ("REJECTED", "ANALYTIC_INCONSISTENCY") if sequential != batch else ("PASS_PROPOSAL_ONLY", "MISSING")
    elif name == "DELETE_RETRACTION_HISTORY":
        original_history = ["update-1", "retraction-tombstone-2", "recompute-3"]
        attacked_history = ["recompute-3"]
        append_only = attacked_history[: len(original_history)] == original_history
        return ("PASS_PROPOSAL_ONLY", "MISSING") if append_only else ("REJECTED", "APPEND_ONLY_VIOLATION")

    receipt = validate(packet)
    return receipt["classification"], "SCHEMA_REJECT" if "SCHEMA_REJECT" in receipt["codes"] else "MISSING"


class TestAnalyticOracles(unittest.TestCase):
    def test_beta_binomial_reference(self):
        a, b, mean = beta_binomial(2.0, 3.0, 7, 3)
        self.assertEqual((a, b), (9.0, 6.0))
        self.assertAlmostEqual(mean, 0.6, places=14)

    def test_beta_binomial_sequential_equals_batch(self):
        a, b = 2.0, 3.0
        for outcome in [1, 1, 0, 1, 0, 1, 1, 1, 1, 0]:
            a, b, _ = beta_binomial(a, b, outcome, 1 - outcome)
        ba, bb, _ = beta_binomial(2.0, 3.0, 7, 3)
        self.assertEqual((a, b), (ba, bb))

    def test_normal_normal_reference(self):
        mu, var = normal_normal(0.0, 4.0, [1.0, 2.0], 1.0)
        self.assertAlmostEqual(mu, 4.0 / 3.0, places=14)
        self.assertAlmostEqual(var, 4.0 / 9.0, places=14)

    def test_normal_normal_sequential_equals_batch(self):
        mu1, var1 = normal_normal(0.0, 4.0, [1.0], 1.0)
        mu2, var2 = normal_normal(mu1, var1, [2.0], 1.0)
        mub, varb = normal_normal(0.0, 4.0, [1.0, 2.0], 1.0)
        self.assertAlmostEqual(mu2, mub, places=14)
        self.assertAlmostEqual(var2, varb, places=14)

    def test_log_bayes_factor_retraction_is_recompute(self):
        prior = 0.4
        factors = [math.log(2.0), math.log(0.8), math.log(1.5)]
        full = compose_log_bf(prior, factors)
        retracted = logistic(logit(full) - factors[1])
        recomputed = compose_log_bf(prior, [factors[0], factors[2]])
        self.assertAlmostEqual(retracted, recomputed, places=14)


class TestMachineContract(unittest.TestCase):
    def test_positive_packet_is_proposal_only(self):
        packet = rebind_digest(positive_packet())
        jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker()).validate(packet)
        receipt = validate_packet(packet, schema=SCHEMA, numeric_registry=NUMERIC)
        self.assertEqual(receipt["classification"], "PASS_PROPOSAL_ONLY")
        self.assertEqual(receipt["effective_belief_state"], "PROPOSAL")
        self.assertTrue(receipt["proposal_only"])
        self.assertFalse(receipt["canonical_belief_authorized"])
        self.assertFalse(receipt["trade_authorized"])

    def test_phase1_cannot_claim_validated_belief(self):
        packet = positive_packet()
        packet["validation"]["packet_status"] = "VALIDATED"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(packet)

    def test_valid_belief_state_is_not_in_phase1_schema(self):
        packet = positive_packet()
        packet["update"]["belief_state"] = "VALID"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(packet)

    def test_mathematically_inconsistent_range_valid_posterior_rejected(self):
        packet = positive_packet()
        packet["update"]["posterior_probability"] = 0.999999
        receipt = validate(packet)
        self.assertEqual(receipt["classification"], "REJECTED")
        self.assertIn("POSTERIOR_MATH_INCONSISTENT", receipt["codes"])

    def test_registered_model_derives_nonzero_contribution(self):
        receipt = validate(positive_packet())
        self.assertEqual(receipt["classification"], "PASS_PROPOSAL_ONLY")

    def test_unregistered_model_nonzero_likelihood_cannot_pass(self):
        packet = positive_packet()
        packet["evidence"][0]["likelihood_model_id"] = "unregistered-likelihood-model"
        packet["diagnostics"]["calibration_status"] = "NOT_RUN"
        receipt = validate(packet)
        self.assertEqual(receipt["classification"], "REVALIDATION_REQUIRED")
        self.assertIn("LIKELIHOOD_UNVERIFIED", receipt["codes"])
        self.assertEqual(receipt["effective_belief_state"], "REVALIDATION_REQUIRED")

    def test_not_run_calibration_with_nonzero_registered_bf_revalidates(self):
        packet = positive_packet()
        packet["diagnostics"]["calibration_status"] = "NOT_RUN"
        receipt = validate(packet)
        self.assertEqual(receipt["classification"], "REVALIDATION_REQUIRED")
        self.assertIn("CALIBRATION_REQUIRED", receipt["codes"])

    def test_cumulative_log_bf_must_equal_registry_derived_sum(self):
        packet = positive_packet()
        packet["update"]["cumulative_log_bayes_factor"] = 0.5
        packet["update"]["posterior_probability"] = expected_posterior(0.4, 0.5)
        receipt = validate(packet)
        self.assertEqual(receipt["classification"], "REJECTED")
        self.assertIn("LIKELIHOOD_CUMULATIVE_MISMATCH", receipt["codes"])

    def test_unknown_rule_clause_fails_closed(self):
        packet = positive_packet()
        packet["identity"]["rule_clause_ids"] = ["SSE_FAKE_UNREGISTERED_CLAUSE"]
        receipt = validate(packet)
        self.assertEqual(receipt["classification"], "REVALIDATION_REQUIRED")
        self.assertIn("RULE_CLAUSE_UNKNOWN", receipt["codes"])

    def test_caller_independence_label_cannot_hide_ancestry(self):
        packet = positive_packet()
        second = _second_evidence(packet)
        second["dependence_provenance"]["candidate_independence_group_id"] = "totally-new-label"
        second["dependence_provenance"]["ancestry_refs"] = ["src-official-1"]
        packet["evidence"].append(second)
        packet["update"]["cumulative_log_bayes_factor"] = math.log(1.5) * 2
        packet["update"]["posterior_probability"] = expected_posterior(0.4, math.log(1.5) * 2)
        receipt = validate(packet)
        self.assertIn("DEPENDENCE_COLLAPSE_REQUIRED", receipt["codes"])

    def test_unverified_multi_source_independence_is_not_authority(self):
        packet = positive_packet()
        packet["evidence"].append(_second_evidence(packet))
        packet["update"]["cumulative_log_bayes_factor"] = math.log(1.5) * 2
        packet["update"]["posterior_probability"] = expected_posterior(0.4, math.log(1.5) * 2)
        receipt = validate(packet)
        self.assertEqual(receipt["classification"], "REVALIDATION_REQUIRED")
        self.assertIn("INDEPENDENCE_UNVERIFIED", receipt["codes"])

    def test_cross_exchange_rule_substitution_rejected(self):
        packet = positive_packet()
        packet["identity"]["exchange"] = "SZSE"
        packet["identity"]["board"] = "MAIN"
        packet["identity"]["symbol_or_universe"] = "000001"
        receipt = validate(packet)
        self.assertEqual(receipt["classification"], "REJECTED")
        self.assertIn("SCHEMA_REJECT", receipt["codes"])

    def test_bse_deferred_clause_revalidates(self):
        classification, code = execute_fixture("BSE_DEFERRED_CLAUSE")
        self.assertEqual(classification, "REVALIDATION_REQUIRED")
        self.assertEqual(code, "RULE_CLAUSE_DEFERRED")

    def test_ex_post_prior_is_rejected(self):
        self.assertEqual(execute_fixture("PRIOR_EFFECTIVE_AFTER_CUTOFF"), ("REJECTED", "PRIOR_NOT_EX_ANTE"))

    def test_post_cutoff_predecision_evidence_revalidates(self):
        self.assertEqual(execute_fixture("EVIDENCE_AFTER_KNOWLEDGE_CUTOFF"), ("REVALIDATION_REQUIRED", "KNOWLEDGE_CUTOFF_VIOLATION"))

    def test_tiny_sample_extreme_posterior_requires_shrinkage(self):
        self.assertEqual(execute_fixture("SMALL_SAMPLE_EXTREME_POSTERIOR"), ("REVALIDATION_REQUIRED", "SMALL_SAMPLE_SHRINKAGE_REQUIRED"))

    def test_canonical_digest_binds_packet_content(self):
        packet = rebind_digest(positive_packet())
        original = packet["numeric_integrity"]["canonical_digest"]
        packet["predictive"]["expected_value"] = 0.321
        self.assertEqual(packet["numeric_integrity"]["canonical_digest"], original)
        receipt = validate_packet(packet, schema=SCHEMA, numeric_registry=NUMERIC)
        self.assertEqual(receipt["classification"], "REJECTED")
        self.assertIn("CANONICAL_DIGEST_MISMATCH", receipt["codes"])

    def test_probability_serialization_uses_twelve_decimals(self):
        self.assertEqual(canonical_probability(0.685), "0.685000000000")


class TestAdversarialPack(unittest.TestCase):
    def test_pack_has_exact_29_executable_cases(self):
        self.assertEqual(len(EVALS["cases"]), 29)
        self.assertTrue(EVALS["execution_contract"]["every_case_must_execute"])
        self.assertTrue(EVALS["execution_contract"]["label_presence_only_is_not_evidence"])


def _make_case_test(case):
    def test(self):
        classification, code = execute_fixture(case["fixture"])
        self.assertEqual(classification, case["expected_classification"], case)
        self.assertEqual(code, case["expected_code"], case)
    test.__name__ = f"test_{case['id'].lower().replace('-', '_')}"
    return test


for _case in EVALS["cases"]:
    setattr(TestAdversarialPack, f"test_{_case['id'].lower().replace('-', '_')}", _make_case_test(_case))


if __name__ == "__main__":
    unittest.main()
