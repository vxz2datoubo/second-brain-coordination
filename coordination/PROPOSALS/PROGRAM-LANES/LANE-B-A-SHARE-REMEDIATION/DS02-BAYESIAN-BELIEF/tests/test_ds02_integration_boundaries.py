import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MATRIX = yaml.safe_load((ROOT / "DS02-INTEGRATION-INTERFACE-MATRIX-v1.0.yaml").read_text(encoding="utf-8"))
SKILL = yaml.safe_load((Path(__file__).resolve().parents[5] / "SKILLS" / "BAYESIAN-BELIEF-UPDATE-FORECAST-FUSION-SKILL-v1.0.yaml").read_text(encoding="utf-8"))
READINESS = yaml.safe_load((ROOT / "PHASE2-IMPLEMENTATION-READINESS-PACKET-v1.0.yaml").read_text(encoding="utf-8"))
NUMERIC = yaml.safe_load((ROOT / "NUMERIC-INTEGRITY-REGISTRY-v1.0.yaml").read_text(encoding="utf-8"))


class TestAuthorityBoundaries(unittest.TestCase):
    def test_all_ds02_authority_flags_false(self):
        self.assertTrue(MATRIX["authority_flags"])
        self.assertFalse(any(MATRIX["authority_flags"].values()))
        self.assertFalse(any(SKILL["skill"]["authority_contract"]["belief_packet_authority_flags"].values()))

    def test_current_phase_is_unvalidated_proposal_only(self):
        self.assertEqual(MATRIX["current_phase"]["packet_semantics"], "UNVALIDATED_PROPOSAL")
        self.assertFalse(MATRIX["current_phase"]["canonical_belief_authorized"])
        self.assertFalse(MATRIX["current_phase"]["validated_posterior_consumer_use_authorized"])
        self.assertFalse(SKILL["skill"]["boundaries"]["canonical_belief_runtime_available"])

    def test_dependence_authority_is_unavailable_and_caller_labels_cannot_substitute(self):
        dep = next(x for x in MATRIX["producer_edges"] if x["producer"] == "FUTURE_DEPENDENCE_AUTHORITY")
        self.assertFalse(dep["currently_available"])
        self.assertFalse(dep["caller_labels_may_substitute"])
        self.assertFalse(NUMERIC["dependence"]["canonical_dependence_authority_available"])
        self.assertFalse(NUMERIC["dependence"]["caller_independence_group_is_authority"])

    def test_w5_rumor_cannot_be_upgraded(self):
        w5 = next(x for x in MATRIX["producer_edges"] if x["producer"] == "W5")
        self.assertFalse(w5["ds02_may_upgrade_rumor_to_fact"])

    def test_w13_bucket_cannot_become_identity(self):
        w13 = next(x for x in MATRIX["producer_edges"] if x["producer"] == "W13")
        self.assertFalse(w13["ds02_may_infer_real_identity_from_bucket"])

    def test_ds11_retains_regime_authority(self):
        ds11 = next(x for x in MATRIX["producer_edges"] if x["producer"] == "DS-11")
        self.assertEqual(ds11["semantic_authority"], "MARKET_REGIME_AND_CHANGE")
        self.assertFalse(ds11["ds02_regime_authority"])

    def test_issue457_retains_epistemic_authority(self):
        ep = next(x for x in MATRIX["producer_edges"] if x["producer"] == "ISSUE_457")
        self.assertFalse(ep["ds02_epistemic_authority"])

    def test_consumers_may_not_treat_phase1_output_as_validated_posterior(self):
        for consumer in MATRIX["consumer_edges"]:
            with self.subTest(consumer=consumer["consumer"]):
                self.assertTrue(consumer["ds02_output_is_advisory_input"])
                self.assertFalse(consumer["may_treat_as_validated_posterior"])

    def test_execution_edges_are_explicitly_forbidden(self):
        forbidden = {tuple(x) for x in MATRIX["forbidden_edges"]}
        for edge in [("DS02", "BROKER"), ("DS02", "LIVE_ORDER"), ("DS02", "ACCOUNT_FUNDS")]:
            self.assertIn(edge, forbidden)
        self.assertIn(("DS02_UNVALIDATED_PROPOSAL", "KELLY_VALIDATED_POSTERIOR_INPUT"), forbidden)
        self.assertIn(("DS02_UNVALIDATED_PROPOSAL", "ALLOCATION_CANONICAL_PROBABILITY"), forbidden)

    def test_phase2_packet_is_not_authority(self):
        self.assertEqual(READINESS["status"], "DESIGN_PREVIEW_ONLY")
        self.assertFalse(READINESS["implementation_authority"])
        self.assertFalse(READINESS["runtime_write_authority"])
        self.assertFalse(READINESS["backtest_write_authority"])
        self.assertEqual(READINESS["stop_condition"], "PACKET_DOES_NOT_AUTHORIZE_RUNTIME_OR_BACKTEST_WRITES")

    def test_phase2_requires_new_prewrite_snapshot(self):
        self.assertIn("NEW_PHASE2_EFFECTIVE_SPEC_SNAPSHOT_PUBLISHED_BEFORE_WRITE", READINESS["preconditions"])


if __name__ == "__main__":
    unittest.main()
