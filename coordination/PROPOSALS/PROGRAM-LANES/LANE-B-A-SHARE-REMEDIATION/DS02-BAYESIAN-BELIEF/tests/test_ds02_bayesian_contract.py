import json
import math
import unittest
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "BELIEF-PACKET-v1.schema.json").read_text(encoding="utf-8"))
EVALS = yaml.safe_load((ROOT / "DS02-ADVERSARIAL-EVALS-v1.0.yaml").read_text(encoding="utf-8"))
NUMERIC = yaml.safe_load((ROOT / "NUMERIC-INTEGRITY-REGISTRY-v1.0.yaml").read_text(encoding="utf-8"))
SOURCES = yaml.safe_load((ROOT / "DS02-RESEARCH-SOURCE-REGISTRY-v1.0.yaml").read_text(encoding="utf-8"))


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


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def admitted_pit(available_at, decision_time):
    return parse_time(available_at) <= parse_time(decision_time)


def positive_packet():
    return {
        "schema": "BeliefPacket/v1",
        "identity": {
            "belief_id": "belief-001",
            "target_id": "CSI300_5D_POSITIVE_RETURN",
            "target_definition_version": "v1",
            "symbol_or_universe": "CSI300",
            "forecast_horizon": "5D",
            "as_of_time": "2026-08-30T01:00:00+08:00",
            "knowledge_cutoff": "2026-08-30T01:00:00+08:00",
            "market_rule_version": "SSE_TRADING_RULES_2026",
            "market_rule_clause_state_version": "SSE_2026_EFFECTIVE_WITH_DECLARED_DEFERRED_PROVISIONS"
        },
        "temporal_provenance": {"decision_time": "2026-08-30T01:00:00+08:00"},
        "prior": {
            "prior_id": "market-base-rate", "prior_version": "v1", "family": "BETA",
            "parameters": {"alpha": 2.0, "beta": 3.0},
            "training_window": "2020-01-01/2025-12-31",
            "effective_from": "2026-01-01T00:00:00+08:00", "evidence_digest": "deadbeef0001"
        },
        "evidence": [{
            "evidence_id": "ev-1", "source_ref": "w5:event:1",
            "source_family_id": "official-exchange", "independence_group_id": "official-exchange-event-1",
            "available_at": "2026-08-29T20:00:00+08:00", "data_snapshot_hash": "cafebabe0001",
            "feature_definition_version": "event-surprise-v1", "polarity": "NON_DIRECTIONAL",
            "likelihood_model_id": "likelihood-1", "likelihood_model_version": "v1", "status": "ADMITTED"
        }],
        "update": {
            "prior_probability": 0.4, "cumulative_log_bayes_factor": math.log(1.5),
            "posterior_probability": compose_log_bf(0.4, [math.log(1.5)]),
            "unknown_mass": 0.1, "belief_state": "VALID"
        },
        "predictive": {
            "expected_value": 0.001,
            "quantiles": {"p05": -0.03, "p25": -0.01, "p50": 0.001, "p75": 0.012, "p95": 0.04},
            "probability_positive": 0.52, "probability_below_loss_threshold": 0.08,
            "predictive_distribution_ref": "artifact://predictive/001"
        },
        "diagnostics": {
            "engine": "analytic-reference", "engine_version": "v1",
            "code_sha": "1a514fe839b1c47a14d7fad4a96e8c9fd2365338", "seed": None,
            "rhat_max": None, "ess_bulk_min": None, "ess_tail_min": None,
            "divergences": None, "pareto_k_max": None,
            "calibration_status": "NOT_RUN", "prior_predictive_status": "NOT_RUN",
            "posterior_predictive_status": "NOT_RUN"
        },
        "numeric_integrity": {
            "probability_serialization_decimals": 12, "rounding_mode": "ROUND_HALF_EVEN",
            "ui_precision_is_authority": False, "canonical_digest": "0123456789abcdef"
        },
        "authority": {
            "market_truth_authority": False, "event_truth_authority": False,
            "regime_authority": False, "epistemic_authority": False,
            "decision_authority": False, "risk_override_authority": False,
            "position_authority": False, "order_authority": False, "trade_authority": False
        }
    }


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


class TestSchemaAndNumericIntegrity(unittest.TestCase):
    def test_positive_packet_validates(self):
        jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker()).validate(positive_packet())

    def test_probability_out_of_range_rejected(self):
        packet = positive_packet(); packet["update"]["posterior_probability"] = 1.00001
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(packet)

    def test_missing_horizon_rejected(self):
        packet = positive_packet(); del packet["identity"]["forecast_horizon"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(packet)

    def test_authority_true_rejected(self):
        packet = positive_packet(); packet["authority"]["order_authority"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(packet)

    def test_canonical_probability_uses_twelve_decimals(self):
        self.assertEqual(canonical_probability(0.685), "0.685000000000")
        self.assertEqual(len(canonical_probability(0.12345678901234).split(".")[1]), 12)

    def test_ui_precision_is_non_authority(self):
        self.assertFalse(NUMERIC["probability"]["ui"]["display_precision_is_authority"])
        self.assertTrue(NUMERIC["probability"]["ui"]["round_trip_from_display_forbidden"])


class TestPointInTimeAndRuleBinding(unittest.TestCase):
    def test_pit_admits_equal_or_earlier(self):
        self.assertTrue(admitted_pit("2026-08-30T01:00:00+08:00", "2026-08-30T01:00:00+08:00"))
        self.assertTrue(admitted_pit("2026-08-29T23:00:00+08:00", "2026-08-30T01:00:00+08:00"))

    def test_pit_rejects_future_available_at(self):
        self.assertFalse(admitted_pit("2026-08-30T01:00:01+08:00", "2026-08-30T01:00:00+08:00"))

    def test_rule_and_clause_state_are_distinct_required_identity(self):
        required = set(SCHEMA["properties"]["identity"]["required"])
        self.assertIn("market_rule_version", required)
        self.assertIn("market_rule_clause_state_version", required)

    def test_bse_registry_records_deferred_clause_semantics(self):
        bse = next(s for s in SOURCES["sources"] if s["id"] == "BSE-TRADING-RULES-2026")
        self.assertIn("deferred", " ".join(bse["supports"]).lower())
        self.assertIn("activation-state", bse["implementation_consequence"])


class TestAdversarialPack(unittest.TestCase):
    def test_eval_pack_has_broad_attack_surface(self):
        self.assertGreaterEqual(len(EVALS["cases"]), 24)
        expected = {"DEPENDENCE_COLLAPSE_REQUIRED", "NOT_CONDITIONALLY_INDEPENDENT", "PIT_VIOLATION",
                    "CALLER_POSTERIOR_NOT_AUTHORITY", "REVALIDATION_REQUIRED", "FORBIDDEN_EDGE",
                    "UNKNOWN_OR_ABSTAIN", "APPEND_ONLY_VIOLATION"}
        self.assertTrue(expected.issubset({case["expected"] for case in EVALS["cases"]}))

    def test_three_independent_analytic_oracles_exist(self):
        ids = {oracle["id"] for oracle in EVALS["analytic_oracles"]}
        self.assertEqual(ids, {"ORACLE-BETA-BINOMIAL-01", "ORACLE-NORMAL-NORMAL-01", "ORACLE-LOG-BF-RETRACTION-01"})


if __name__ == "__main__":
    unittest.main()
