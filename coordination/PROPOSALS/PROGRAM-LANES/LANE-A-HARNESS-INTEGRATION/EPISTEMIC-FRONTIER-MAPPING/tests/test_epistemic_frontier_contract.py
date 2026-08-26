from pathlib import Path
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[5]
SKILL = ROOT / "SKILLS" / "EPISTEMIC-KNOWLEDGE-STATE-FRONTIER-MAPPING-SKILL-v1.0.yaml"
EVALS = Path(__file__).resolve().parents[1] / "EPISTEMIC-FRONTIER-EVALS-v1.0.yaml"


class EpistemicFrontierContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = yaml.safe_load(SKILL.read_text(encoding="utf-8"))
        cls.evals = yaml.safe_load(EVALS.read_text(encoding="utf-8"))

    def test_single_authority_reuse_boundaries(self):
        reuse = self.skill["canonical_reuse"]
        self.assertEqual(reuse["knowledge_memory_truth_owner"], "W3_SECOND_BRAIN")
        self.assertEqual(reuse["personal_cognitive_model_owner"], "PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-0010")
        self.assertEqual(reuse["formal_skill_truth_owner"], "EXISTING_FORMAL_SKILL_GOVERNANCE")
        self.assertTrue(reuse["no_new_memory_runtime"])
        self.assertTrue(reuse["no_new_knowledge_graph_authority"])
        self.assertTrue(reuse["no_new_personal_profile_authority"])
        self.assertTrue(reuse["no_new_mastery_authority"])
        self.assertTrue(reuse["no_new_skill_authority"])

    def test_state_key_and_projection_contract_are_consistent(self):
        projection = self.skill["EpistemicStateProjection_v1"]
        required = set(projection["required"])
        fields = set(projection["fields"])
        self.assertTrue(required <= fields)
        self.assertTrue(set(self.skill["state_key"]["required"]) <= required)
        for field in (
            "projection_version",
            "access_disposition",
            "knowledge_claim_polarity",
            "confidence_basis",
            "inference_policy_ref",
            "readiness_policy_ref",
            "last_evaluated_at",
        ):
            self.assertIn(field, required)

    def test_epistemic_outcomes_do_not_confuse_scope_with_knowledge(self):
        projection = self.skill["EpistemicStateProjection_v1"]["fields"]
        cognitive = set(projection["cognitive_band"]["enum"])
        access = set(projection["access_disposition"]["enum"])
        self.assertNotIn("SCOPE_FORBIDDEN", cognitive)
        self.assertIn("SCOPE_FORBIDDEN", access)
        self.assertIn("UNOBSERVED", cognitive)
        self.assertIn("UNKNOWN", cognitive)
        self.assertIn("ABSTAIN", cognitive)

    def test_user_correction_and_polarity_are_first_class(self):
        evidence_order = self.skill["EvidencePriority_v1"]["order"]
        self.assertEqual(evidence_order[0], "USER_CORRECTION")
        polarities = set(self.skill["EpistemicStateProjection_v1"]["fields"]["knowledge_claim_polarity"]["enum"])
        self.assertIn("AFFIRMS_KNOWLEDGE", polarities)
        self.assertIn("DENIES_KNOWLEDGE", polarities)
        invariants = self.skill["EpistemicStateProjection_v1"]["invariants"]
        self.assertTrue(any("DENIES_KNOWLEDGE" in item and "KNOWN_UNSAID_INFERRED" in item for item in invariants))

    def test_caller_cannot_supply_classification_authority(self):
        policy = self.skill["ClassificationPolicyBinding_v1"]
        self.assertEqual(policy["numeric_thresholds"], "NOT_FROZEN_IN_THIS_SLICE")
        self.assertEqual(policy["required_policy_refs"]["KNOWN_UNSAID_INFERRED"], "inference_policy_ref")
        self.assertEqual(policy["required_policy_refs"]["UNKNOWN_BUT_ACCESSIBLE"], "readiness_policy_ref")
        self.assertTrue(any("caller numeric threshold" in item for item in policy["policy_requirements"]))

    def test_cross_domain_transfer_and_prerequisite_cycles_fail_closed(self):
        policy = self.skill["PrerequisiteGraphPolicy_v1"]
        self.assertEqual(policy["cycle_policy"], "FAIL_CLOSED")
        self.assertEqual(policy["cycle_outcome"], "CYCLIC_OR_INVALID")
        self.assertFalse(policy["on_cycle"]["frontier_recommendation_authorized"])
        self.assertFalse(policy["on_cycle"]["mastery_inference_authorized"])
        self.assertFalse(policy["cross_domain_policy"]["target_domain_known_inference_without_target_evidence"])

    def test_external_crosswalk_requires_version_provenance_and_no_close_match_merge(self):
        record = self.skill["ExternalCrosswalkRecord_v1"]
        required = set(record["required"])
        self.assertTrue({"source_system", "source_version", "source_ref", "target_ref", "mapping_relation", "provenance_refs"} <= required)
        self.assertTrue(any("CLOSE_MATCH" in item and "identity merge" in item for item in record["invariants"]))
        for adapter in self.skill["ExternalCrosswalkRegistry_v1"]["adapters"].values():
            self.assertNotEqual(adapter["authority"], "CANONICAL")

    def test_research_frontier_routes_to_gap_compiler_without_skill_promotion(self):
        scanner = self.skill["ResearchFrontierScanner_v1"]
        self.assertEqual(scanner["downstream"], "BLUEPRINT-TO-SKILL-GAP-COMPILER-0012")
        self.assertIn("automatic Formal Skill promotion", scanner["forbidden"])
        self.assertIn("citation-count-only quality authority", scanner["forbidden"])

    def test_sensitive_profile_inference_and_trade_authority_remain_forbidden(self):
        forbidden = self.skill["safety_and_profile_boundaries"]["forbidden"]
        joined = "\n".join(forbidden).lower()
        for word in ("political", "religious", "health", "global intelligence"):
            self.assertIn(word, joined)
        self.assertIn("NO_TRADE", self.skill["boundary"])
        self.assertEqual(self.skill["maturity"]["formal_skill_promotion"], "NOT_AUTHORIZED")
        self.assertTrue(self.skill["maturity"]["runtime_not_implemented"])

    def test_adversarial_eval_suite_covers_required_failure_modes(self):
        ids = {case["case_id"] for case in self.evals["cases"]}
        expected = {
            "EKM-EVAL-003-SIMILARITY-ONLY",
            "EKM-EVAL-004-EXPLICIT-DENIAL-OVERRIDES-INFERENCE",
            "EKM-EVAL-007-CROSS-DOMAIN-NEGATIVE-TRANSFER",
            "EKM-EVAL-008-PREREQUISITE-CYCLE",
            "EKM-EVAL-009-CROSSWALK-CLOSE-NOT-EXACT",
            "EKM-EVAL-010-STALE-FINANCIAL-KNOWLEDGE",
            "EKM-EVAL-011-RESEARCH-FRONTIER-IS-NOT-SKILL-AUTHORITY",
            "EKM-EVAL-012-SCOPE-FORBIDDEN",
            "EKM-EVAL-013-SENSITIVE-PROFILE-INFERENCE",
            "EKM-EVAL-014-CALLER-CONTROLLED-THRESHOLD",
            "EKM-EVAL-015-MISSING-PROVENANCE",
        }
        self.assertTrue(expected <= ids)
        self.assertEqual(self.evals["boundary"], "SYNTHETIC_PUBLIC_SAFE / NO_RUNTIME_AUTHORIZATION / NO_TRADE")


if __name__ == "__main__":
    unittest.main()
