from pathlib import Path
import unittest

import yaml


HERE = Path(__file__).resolve().parents[1]
INTERFACES = HERE / "DS02-INTEGRATION-INTERFACE-MATRIX-v1.0.yaml"


class DS02IntegrationBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = yaml.safe_load(INTERFACES.read_text(encoding="utf-8"))

    def test_ds02_is_probability_bus_not_second_source_authority(self):
        principles = "\n".join(self.matrix["principles"])
        self.assertIn("BELIEVE/probability bus", principles)
        self.assertIn("not a second source-of-truth runtime", principles)
        self.assertIn("No direct DS-02 to broker/order edge", principles)

    def test_upstream_owners_retain_authority(self):
        producers = self.matrix["producers"]
        self.assertEqual(producers["W2"]["retains_authority"], "MARKET_AND_REPLAY")
        self.assertFalse(producers["W2"]["ds02_may_mutate_upstream_truth"])
        self.assertEqual(producers["W5"]["retains_authority"], "EVENT_EVIDENCE")
        self.assertFalse(producers["W5"]["ds02_may_upgrade_rumor_to_fact"])
        self.assertEqual(producers["W13"]["retains_authority"], "PARTICIPANT_FLOW_CONTEXT")
        self.assertFalse(producers["W13"]["ds02_may_infer_real_participant_identity_from_vendor_bucket"])
        self.assertEqual(producers["DS11"]["retains_authority"], "REGIME_CHANGE_MODEL_DECAY")
        self.assertFalse(producers["DS11"]["ds02_may_create_second_regime_authority"])
        self.assertEqual(producers["EPISTEMIC_SKILL_0013"]["retains_authority"], "EPISTEMIC_PROJECTION")
        self.assertFalse(producers["EPISTEMIC_SKILL_0013"]["ds02_may_create_second_user_profile"])

    def test_multi_agent_forecasts_must_preserve_dependence_metadata(self):
        agent = self.matrix["producers"]["MULTI_AGENT_GAME_ENGINE"]
        provided = set(agent["provides"])
        self.assertTrue(
            {"shared_training_data_group", "shared_feature_group", "shared_model_family", "provenance_refs"}
            <= provided
        )
        self.assertIn("dependence-aware", agent["ds02_requirement"])
        self.assertIn("no independent-vote assumption", agent["ds02_requirement"])

    def test_downstream_consumers_are_risk_decision_allocation_and_audit(self):
        consumers = self.matrix["consumers"]
        self.assertTrue({"W7", "W10", "W11", "ISSUE_62_KELLY_THORP", "DS10"} <= set(consumers))
        self.assertTrue(consumers["W7"]["may_apply_independent_risk_gates"])
        self.assertFalse(consumers["W7"]["may_override_ds02_probability"])
        self.assertIn("freeze the ex-ante belief identity", consumers["W10"]["required_behavior"])
        self.assertIn("probability alone cannot determine position size", consumers["W11"]["rule"])
        self.assertIn("uncalibrated", consumers["ISSUE_62_KELLY_THORP"]["hard_gate"])
        self.assertIn("may not self-certify alpha", consumers["DS10"]["rule"])

    def test_forbidden_edges_include_live_execution_and_canonical_write_escalation(self):
        edges = {tuple(edge) for edge in self.matrix["forbidden_edges"]}
        required = {
            ("DS02", "BROKER"),
            ("DS02", "LIVE_ORDER"),
            ("DS02", "ACCOUNT_FUNDS"),
            ("DS02", "W5_CANONICAL_EVENT_WRITE"),
            ("DS02", "W2_CANONICAL_MARKET_WRITE"),
            ("DS02", "DS11_CANONICAL_REGIME_WRITE"),
            ("DS02", "EPISTEMIC_CANONICAL_PROFILE_WRITE"),
        }
        self.assertTrue(required <= edges)

    def test_handoff_requires_provenance_dependence_and_invalidation(self):
        handoff = self.matrix["handoff_contract"]
        upstream = set(handoff["upstream_to_ds02_required"])
        downstream = set(handoff["ds02_to_downstream_required"])
        self.assertTrue(
            {"semantic_version", "point_in_time_availability", "provenance_ref", "independence/dependence metadata", "invalidation_conditions"}
            <= upstream
        )
        self.assertTrue(
            {"belief_id", "target_definition_version", "market_rule_version", "unknown_mass", "calibration status", "regime validity", "provenance digest", "authority_flags_all_false"}
            <= downstream
        )


if __name__ == "__main__":
    unittest.main()
