from copy import deepcopy
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
import json
import math
from pathlib import Path
import unittest

import yaml
from jsonschema import Draft202012Validator


COORDINATION = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parents[1]
SKILL = COORDINATION / "SKILLS" / "BAYESIAN-BELIEF-UPDATE-FORECAST-FUSION-SKILL-v1.0.yaml"
EVALS = HERE / "DS02-ADVERSARIAL-EVALS-v1.0.yaml"
SOURCES = HERE / "DS02-RESEARCH-SOURCE-REGISTRY-v1.0.yaml"
NUMERIC = HERE / "NUMERIC-INTEGRITY-REGISTRY-v1.0.yaml"
SCHEMA = HERE / "BELIEF-PACKET-v1.schema.json"


def beta_binomial_posterior(alpha, beta, observations):
    successes = sum(observations)
    failures = len(observations) - successes
    return alpha + successes, beta + failures


def beta_mean(alpha, beta):
    return alpha / (alpha + beta)


def parse_time(value):
    return datetime.fromisoformat(value)


class DS02BayesianContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = yaml.safe_load(SKILL.read_text(encoding="utf-8"))
        cls.evals = yaml.safe_load(EVALS.read_text(encoding="utf-8"))
        cls.sources = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
        cls.numeric = yaml.safe_load(NUMERIC.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema)

    def test_skill_identity_and_no_trade_boundary(self):
        self.assertEqual(
            self.skill["skill_id"],
            "BAYESIAN-BELIEF-UPDATE-FORECAST-FUSION-SKILL-0012B",
        )
        self.assertEqual(self.skill["lifecycle_stage"], "BELIEVE")
        self.assertEqual(self.skill["priority"], "P0")
        self.assertIn("NO_TRADE", self.skill["boundary"])
        self.assertFalse(self.skill["first_slice"]["runtime_implementation_authorized"])
        self.assertEqual(self.skill["first_slice"]["live_trade"], "PROHIBITED")

    def test_single_authority_boundaries(self):
        systems = self.skill["systems_of_record"]
        self.assertEqual(systems["market_and_replay"], "W2")
        self.assertEqual(systems["event_evidence"], "W5")
        self.assertEqual(systems["risk"], "W7")
        self.assertEqual(systems["decision_freeze"], "W10")
        self.assertEqual(systems["allocation_consumer"], "W11")
        self.assertEqual(systems["probability_and_belief"], "W12")
        self.assertEqual(systems["participant_flow_context"], "W13")
        self.assertIn("Issue #62", systems["downstream_kelly"])
        self.assertIn("0013", systems["epistemic_projection"])

    def test_all_authority_flags_are_false(self):
        flags = self.skill["authority_flags"]
        self.assertTrue(flags)
        self.assertTrue(all(value is False for value in flags.values()))
        self.assertFalse(flags["trade_authority"])
        self.assertFalse(flags["order_authority"])
        self.assertFalse(flags["position_authority"])
        self.assertFalse(flags["decision_authority"])

    def test_forecast_target_requires_explicit_horizon_and_rule_version(self):
        required = set(self.skill["forecast_target_contract"]["required_fields"])
        self.assertTrue(
            {"target_id", "target_definition_version", "forecast_horizon", "as_of_time", "knowledge_cutoff", "market_rule_version"}
            <= required
        )
        self.assertEqual(
            self.skill["forecast_target_contract"]["initial_a_share_horizons"],
            ["INTRADAY", "1D", "3D", "5D", "10D", "20D", "60D"],
        )

    def test_beta_binomial_analytic_case(self):
        case = self.evals["analytic_cases"][0]
        alpha, beta = beta_binomial_posterior(
            case["prior"]["alpha"], case["prior"]["beta"], case["observations"]
        )
        self.assertEqual(alpha, case["expected"]["posterior_alpha"])
        self.assertEqual(beta, case["expected"]["posterior_beta"])
        self.assertAlmostEqual(beta_mean(alpha, beta), case["expected"]["posterior_mean"], places=15)
        naive = sum(case["observations"]) / len(case["observations"])
        self.assertNotAlmostEqual(beta_mean(alpha, beta), naive, places=12)

    def test_sequential_equals_batch_for_conjugate_case(self):
        case = self.evals["analytic_cases"][1]
        batch = beta_binomial_posterior(
            case["prior"]["alpha"], case["prior"]["beta"], case["observations"]
        )
        alpha = case["prior"]["alpha"]
        beta = case["prior"]["beta"]
        for observation in case["observations"]:
            alpha, beta = beta_binomial_posterior(alpha, beta, [observation])
        sequential = (alpha, beta)
        self.assertEqual(batch, sequential)
        self.assertEqual(batch, (case["expected"]["posterior_alpha"], case["expected"]["posterior_beta"]))
        self.assertAlmostEqual(beta_mean(*batch), case["expected"]["posterior_mean"], places=15)

    def test_copied_media_collapses_to_one_independence_group(self):
        case = next(c for c in self.evals["cases"] if c["case_id"] == "DS02-EVAL-001-COPIED-MEDIA-NOT-INDEPENDENT")
        groups = {row["independence_group_id"] for row in case["evidence"]}
        families = {row["source_family_id"] for row in case["evidence"]}
        self.assertEqual(len(groups), case["expected"]["independent_evidence_groups"])
        self.assertEqual(len(families), 1)
        self.assertFalse(case["expected"]["naive_four_factor_multiplication_authorized"])

    def test_multi_agent_shared_feed_cannot_mint_independence(self):
        case = next(c for c in self.evals["cases"] if c["case_id"] == "DS02-EVAL-002-MULTI-AGENT-SHARED-FEED")
        training_groups = {row["shared_training_data_group"] for row in case["forecasts"]}
        feature_groups = {row["shared_feature_group"] for row in case["forecasts"]}
        self.assertEqual(len(training_groups), 1)
        self.assertEqual(len(feature_groups), 1)
        self.assertFalse(case["expected"]["four_independent_forecasters_assumption_authorized"])
        self.assertTrue(case["expected"]["dependence_matrix_required"])

    def test_point_in_time_future_leak_fails(self):
        case = next(c for c in self.evals["cases"] if c["case_id"] == "DS02-EVAL-005-PIT-FUTURE-LEAK")
        available_at = parse_time(case["evidence"]["available_at"])
        decision_time = parse_time(case["decision_time"])
        self.assertGreater(available_at, decision_time)
        self.assertFalse(case["expected"]["evidence_admissible"])
        self.assertEqual(self.numeric["point_in_time_contract"]["admission_rule"], "available_at <= decision_time")

    def test_rule_change_requires_revalidation(self):
        case = next(c for c in self.evals["cases"] if c["case_id"] == "DS02-EVAL-006-RULE-VERSION-BREAK")
        self.assertNotEqual(
            case["historical_observation"]["market_rule_version"],
            case["target_context"]["market_rule_version"],
        )
        self.assertFalse(case["expected"]["silent_pooling_authorized"])
        self.assertEqual(case["expected"]["likelihood_state"], "REVALIDATION_REQUIRED")
        self.assertIn("market_rule_change", self.skill["regime_policy"]["invalidation_triggers"])

    def test_current_exchange_rule_sources_are_versioned_and_scoped(self):
        by_id = {row["source_id"]: row for row in self.sources["sources"]}
        expected = {
            "SSE-TRADING-RULES-2026": "2026-07-06",
            "SZSE-TRADING-RULES-2026": "2026-07-06",
            "BSE-TRADING-RULES-2026": "2026-07-06",
        }
        for source_id, effective in expected.items():
            self.assertEqual(by_id[source_id]["source_grade"], "A1_OFFICIAL_PRIMARY")
            self.assertEqual(by_id[source_id]["effective_date"], effective)
            self.assertTrue(by_id[source_id]["supported_claims"])
            self.assertTrue(by_id[source_id]["not_supported_claims"])
        self.assertEqual(by_id["BSE-TRADING-RULES-2026"]["status"], "CURRENT_EFFECTIVE_WITH_DEFERRED_CLAUSES")

    def test_research_sources_have_claim_scope_and_non_claim_scope(self):
        for row in self.sources["sources"]:
            self.assertTrue(row["supported_claims"], row["source_id"])
            self.assertTrue(row["not_supported_claims"], row["source_id"])
            self.assertTrue(str(row["url"]).startswith("https://"), row["source_id"])
        ids = {row["source_id"] for row in self.sources["sources"]}
        self.assertTrue({"PYMC-PRIOR-POSTERIOR-PREDICTIVE", "STAN-RHAT-ESS", "ARVIZ-PSIS-LOO", "TALTS-SBC-2018", "ADAMS-MACKAY-BOCPD", "GNEITING-RAFTERY-2007"} <= ids)

    def test_numeric_precision_and_ui_rounding_are_separate(self):
        policy = self.numeric["canonical_numeric_policy"]
        self.assertEqual(policy["probability_internal_type"], "float64")
        self.assertEqual(policy["probability_serialization_decimal_places"], 12)
        self.assertFalse(self.skill["numeric_integrity"]["ui_display_is_truth"])
        value = Decimal("0.68329407124549")
        quantized = value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN)
        self.assertEqual(str(quantized), "0.683294071245")
        ui = (quantized * Decimal(100)).quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)
        self.assertEqual(str(ui), "68.3")
        self.assertNotEqual(Decimal("0.683"), quantized)

    def test_feature_polarity_and_target_definition_cannot_silently_drift(self):
        contract = self.numeric["feature_definition_contract"]
        self.assertIn("polarity_changes", contract["version_bump_required_when"])
        self.assertIn("mathematical_definition_changes", contract["version_bump_required_when"])
        labels = self.numeric["label_registry"]
        self.assertEqual(labels["RET-CLOSE-CLOSE-5D"]["definition"], "close[t+5] / close[t] - 1")
        self.assertEqual(labels["RET-CLOSE-CLOSE-5D"]["horizon"], "5D")

    def test_unknown_likelihood_preserves_abstention(self):
        case = next(c for c in self.evals["cases"] if c["case_id"] == "DS02-EVAL-010-UNKNOWN-LIKELIHOOD")
        self.assertIsNone(case["evidence"]["likelihood_model_id"])
        self.assertFalse(case["expected"]["invented_bayes_factor_authorized"])
        self.assertTrue(case["expected"]["unknown_mass_required"])
        self.assertEqual(case["expected"]["disposition"], "ABSTAIN")
        self.assertTrue(self.skill["unknown_policy"]["unknown_mass_required_when_material"])

    def test_high_posterior_has_no_action_authority(self):
        case = next(c for c in self.evals["cases"] if c["case_id"] == "DS02-EVAL-011-HIGH-POSTERIOR-NO-TRADE")
        self.assertGreater(case["posterior_probability"], 0.8)
        self.assertLess(case["payoff_distribution"]["loss_if_wrong"], -0.05)
        self.assertFalse(case["expected"]["buy_authority"])
        self.assertEqual(case["expected"]["route_to"], ["W7", "W10", "W11"])

    def test_schema_accepts_valid_packet_and_rejects_authority_escalation(self):
        packet = self._valid_packet()
        errors = list(self.validator.iter_errors(packet))
        self.assertEqual(errors, [], [e.message for e in errors])

        escalated = deepcopy(packet)
        escalated["authority_flags"]["trade_authority"] = True
        errors = list(self.validator.iter_errors(escalated))
        self.assertTrue(errors)

        out_of_range = deepcopy(packet)
        out_of_range["update"]["posterior_probability"] = 1.2
        errors = list(self.validator.iter_errors(out_of_range))
        self.assertTrue(errors)

        missing_horizon = deepcopy(packet)
        del missing_horizon["identity"]["forecast_horizon"]
        errors = list(self.validator.iter_errors(missing_horizon))
        self.assertTrue(errors)

    def test_posterior_predictive_requires_distribution_shape_not_one_scalar(self):
        schema_predictive = self.schema["properties"]["predictive"]
        required = set(schema_predictive["required"])
        self.assertTrue({"expected_value", "p05", "p25", "p50", "p75", "p95", "probability_positive", "probability_below_loss_threshold", "predictive_distribution_ref"} <= required)
        self.assertNotEqual(required, {"posterior_probability"})

    def test_adversarial_suite_covers_core_failure_families(self):
        ids = {case["case_id"] for case in self.evals["cases"]}
        required = {
            "DS02-EVAL-001-COPIED-MEDIA-NOT-INDEPENDENT",
            "DS02-EVAL-002-MULTI-AGENT-SHARED-FEED",
            "DS02-EVAL-003-LLM-CONFIDENCE",
            "DS02-EVAL-005-PIT-FUTURE-LEAK",
            "DS02-EVAL-006-RULE-VERSION-BREAK",
            "DS02-EVAL-008-TARGET-NAME-COLLISION",
            "DS02-EVAL-009-FEATURE-POLARITY-CONFLICT",
            "DS02-EVAL-010-UNKNOWN-LIKELIHOOD",
            "DS02-EVAL-011-HIGH-POSTERIOR-NO-TRADE",
            "DS02-EVAL-012-EVIDENCE-RETRACTION",
            "DS02-EVAL-015-CALLER-SUPPLIED-POSTERIOR",
            "DS02-EVAL-016-DATA-REVISION-LEAK",
            "DS02-EVAL-017-EXCHANGE-RULE-SUBSTITUTION",
            "DS02-EVAL-018-REGIME-DRIFT",
            "DS02-EVAL-019-MISSING-HORIZON",
            "DS02-EVAL-020-AUTHORITY-BOUNDARY",
        }
        self.assertTrue(required <= ids)
        self.assertIn("NO_TRADE", self.evals["boundary"])

    @staticmethod
    def _valid_packet():
        return {
            "schema_version": "BeliefPacket/v1",
            "belief_id": "BELIEF-SYNTHETIC-001",
            "identity": {
                "target_id": "RET-CLOSE-CLOSE-5D",
                "target_definition_version": "1.0",
                "symbol_or_universe": "SYNTHETIC",
                "exchange": "SSE",
                "board": "MAIN",
                "security_type": "A_SHARE",
                "forecast_horizon": "5D",
                "as_of_time": "2026-08-31T10:00:00+08:00",
                "knowledge_cutoff": "2026-08-31T10:00:00+08:00",
                "market_rule_version": "SSE-TRADING-RULES-2026",
            },
            "temporal_provenance": {
                "event_time": "2026-08-31T09:30:00+08:00",
                "published_at": "2026-08-31T09:31:00+08:00",
                "available_at": "2026-08-31T09:31:01+08:00",
                "market_effective_at": "2026-08-31T09:31:01+08:00",
                "ingested_at": "2026-08-31T09:31:02+08:00",
            },
            "prior": {
                "prior_id": "PRIOR-001",
                "prior_version": "1.0",
                "prior_family": "empirical_base_rate",
                "prior_parameters": {"alpha": 2.0, "beta": 2.0},
                "prior_training_window": "2024-01-01/2026-06-30",
                "prior_regime_scope": ["SYNTHETIC"],
                "prior_effective_from": "2026-07-01",
                "prior_evidence_digest": "sha256:synthetic",
            },
            "evidence": [
                {
                    "evidence_id": "EV-001",
                    "evidence_type": "SYNTHETIC",
                    "source_ref": "SRC-001",
                    "source_grade": "SYNTHETIC",
                    "source_family_id": "FAMILY-001",
                    "independence_group_id": "GROUP-001",
                    "feature_definition_version": "1.0",
                    "feature_value": 1.0,
                    "feature_unit": "unitless",
                    "feature_polarity": "POSITIVE_IS_SUPPORTIVE",
                    "likelihood_model_id": "LIK-001",
                    "likelihood_model_version": "1.0",
                    "valid_from": "2026-08-31T09:31:01+08:00",
                    "valid_until": None,
                    "data_snapshot_hash": "sha256:synthetic-data",
                }
            ],
            "update": {
                "prior_probability": 0.5,
                "prior_log_odds": 0.0,
                "log_bayes_factor_by_evidence": {"EV-001": math.log(2.0)},
                "cumulative_log_bayes_factor": math.log(2.0),
                "posterior_probability": 2.0 / 3.0,
                "posterior_log_odds": math.log(2.0),
                "posterior_family": "synthetic",
                "posterior_parameters": {},
                "unknown_mass": 0.0,
            },
            "ensemble": {
                "forecast_models": ["M1"],
                "model_versions": ["1.0"],
                "dependence_matrix_ref": "DEP-001",
                "model_weights": [1.0],
                "ensemble_method": "single_model",
                "ensemble_version": "1.0",
            },
            "regime": {
                "market_regime_posterior": {"SYNTHETIC": 1.0},
                "volatility_regime_posterior": {"SYNTHETIC": 1.0},
                "liquidity_regime_posterior": {"SYNTHETIC": 1.0},
                "policy_regime_posterior": {"SYNTHETIC": 1.0},
                "changepoint_probability": 0.0,
                "validity_window": "2026-08-31",
                "regime_model_version": "DS11-SYNTHETIC-1.0",
            },
            "predictive": {
                "expected_value": 0.01,
                "median": 0.008,
                "p05": -0.03,
                "p25": -0.005,
                "p50": 0.008,
                "p75": 0.02,
                "p95": 0.05,
                "probability_positive": 0.66,
                "probability_below_loss_threshold": 0.08,
                "predictive_distribution_ref": "PRED-SYNTHETIC-001",
            },
            "diagnostics": {
                "inference_engine": "analytic",
                "inference_engine_version": "1.0",
                "code_commit_sha": "synthetic0",
                "random_seed": None,
                "rhat_max": None,
                "ess_bulk_min": None,
                "ess_tail_min": None,
                "divergent_transition_count": None,
                "prior_predictive_status": "PASS",
                "posterior_predictive_status": "PASS",
                "simulation_based_calibration_status": "NOT_APPLICABLE_ANALYTIC_FIXTURE",
                "psis_loo_status": "NOT_APPLICABLE",
                "pareto_k_max": None,
                "calibration_status": "SYNTHETIC_ONLY",
                "calibration_model_version": "NONE",
            },
            "numeric_integrity": {
                "probability_serialization_decimal_places": 12,
                "rounding_policy_version": "DS02-ROUNDING-1.0",
                "numeric_tolerance_registry_ref": "DS02-TOLERANCE-1.0",
                "feature_polarity_registry_ref": "DS02-NUMERIC-INTEGRITY-REGISTRY-0012B",
                "canonical_digest": "sha256:synthetic-packet",
            },
            "authority_flags": {
                "market_truth_authority": False,
                "event_truth_authority": False,
                "regime_truth_authority": False,
                "decision_authority": False,
                "risk_override_authority": False,
                "position_authority": False,
                "order_authority": False,
                "trade_authority": False,
            },
        }


if __name__ == "__main__":
    unittest.main()
