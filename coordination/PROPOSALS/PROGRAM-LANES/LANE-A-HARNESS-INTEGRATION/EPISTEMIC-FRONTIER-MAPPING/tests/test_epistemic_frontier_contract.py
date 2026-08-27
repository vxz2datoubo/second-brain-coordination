from copy import deepcopy
from pathlib import Path
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[5]
SKILL = ROOT / "SKILLS" / "EPISTEMIC-KNOWLEDGE-STATE-FRONTIER-MAPPING-SKILL-v1.0.yaml"
EVALS = Path(__file__).resolve().parents[1] / "EPISTEMIC-FRONTIER-EVALS-v1.0.yaml"


def _has_cycle(edges):
    graph = {}
    for source, target in edges:
        graph.setdefault(source, set()).add(target)
        graph.setdefault(target, set())

    visiting = set()
    visited = set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbor in graph.get(node, ()):
            if visit(neighbor):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def _derive_expected(case):
    """Deterministic public-safe reference semantics for the frozen eval contract.

    This is intentionally test/eval-only. It does not implement a production W3,
    PEOS, profile, or skill runtime. The fixture's ``expected`` section is data
    under test, not authority: critical outcomes are derived independently from
    the case inputs below and then compared field-for-field.
    """
    evidence = case.get("evidence", {})
    policy = case.get("policy", {})
    modes = set(evidence.get("modes", []))
    polarity = evidence.get("knowledge_claim_polarity")
    provenance = evidence.get("provenance_refs")

    if policy.get("access_disposition") == "SCOPE_FORBIDDEN":
        return {
            "projection_authorized": False,
            "no_cross_scope_fallback": True,
        }

    requested = str(case.get("requested_inference", "")).lower()
    if requested and any(term in requested for term in ("political", "religious", "health")):
        return {
            "authorized": False,
            "disposition": "ABSTAIN",
        }

    if "caller_numeric_threshold" in policy and not policy.get("inference_policy_ref"):
        return {
            "cognitive_band_authorized": False,
            "reason": "VERSIONED_CLASSIFICATION_POLICY_REQUIRED",
        }

    if provenance == []:
        return {
            "cognitive_band_authorized": False,
            "reason": "PROVENANCE_REQUIRED",
        }

    graph = case.get("prerequisite_graph")
    if graph is not None and _has_cycle(graph.get("edges", [])):
        return {
            "prerequisite_coverage": "CYCLIC_OR_INVALID",
            "frontier_recommendation_authorized": False,
        }

    crosswalk = case.get("crosswalk")
    if crosswalk is not None and crosswalk.get("mapping_relation") == "CLOSE_MATCH":
        return {
            "canonical_identity_merge_authorized": False,
            "transitive_exact_match_authorized": False,
        }

    research_candidate = case.get("research_candidate")
    if research_candidate is not None:
        return {
            "downstream": "BLUEPRINT-TO-SKILL-GAP-COMPILER-0012",
            "automatic_formal_skill_promotion": False,
        }

    if evidence.get("freshness_status") == "STALE":
        return {
            "cognitive_state_may_remain_known": True,
            "current_method_validity": "REVALIDATION_REQUIRED",
            "trading_authority": False,
        }

    if evidence.get("pure_similarity_only"):
        return {
            "forbidden_cognitive_bands": ["KNOWN_UNSAID_INFERRED", "KNOWN_SAID"],
            "allowed_outcomes": ["UNOBSERVED", "UNKNOWN", "ABSTAIN"],
        }

    if polarity == "DENIES_KNOWLEDGE" and "USER_CORRECTION" in modes:
        return {
            "forbidden_cognitive_bands": ["KNOWN_UNSAID_INFERRED"],
            "correction_must_be_current_authority_for_user_claim": True,
            "historical_inference_must_remain_traceable": True,
        }

    source_domain = evidence.get("source_domain")
    target_domain = evidence.get("target_domain")
    target_domain_evidence_present = evidence.get(
        "target_domain_evidence_present",
        policy.get("target_domain_evidence_present"),
    )
    if source_domain and target_domain and source_domain != target_domain and target_domain_evidence_present is False:
        return {
            "forbidden_cognitive_bands": ["KNOWN_UNSAID_INFERRED"],
            "allowed_outcomes": [
                "UNKNOWN_BUT_ACCESSIBLE",
                "UNKNOWN_REQUIRES_SCAFFOLDING",
                "UNKNOWN",
                "ABSTAIN",
            ],
        }

    if polarity == "AFFIRMS_KNOWLEDGE" and "USER_EXPLICIT" in modes:
        return {
            "cognitive_band": "KNOWN_SAID",
            "mastery_must_remain_independent": True,
        }

    if (
        polarity == "DEMONSTRATES_COMPETENCE"
        and policy.get("inference_policy_ref")
        and target_domain_evidence_present is not False
        and modes.intersection({"DIRECT_TASK_DEMONSTRATION", "REPEATED_BEHAVIORAL_EVIDENCE"})
    ):
        return {
            "cognitive_band": "KNOWN_UNSAID_INFERRED",
            "may_not_be_represented_as_user_explicit": True,
        }

    if (
        polarity == "DOES_NOT_ESTABLISH_KNOWLEDGE"
        and policy.get("prerequisite_coverage") == "SUFFICIENT"
        and policy.get("readiness_policy_ref")
    ):
        return {
            "cognitive_band": "UNKNOWN_BUT_ACCESSIBLE",
            "must_not_imply_user_does_not_know": True,
            "probe_allowed": True,
        }

    if (
        polarity == "UNKNOWN"
        and policy.get("prerequisite_coverage") == "MISSING"
        and policy.get("readiness_policy_ref")
    ):
        return {
            "cognitive_band": "UNKNOWN_REQUIRES_SCAFFOLDING",
            "required_scaffold": "PREREQUISITE_CONCEPT",
        }

    raise AssertionError(f"No deterministic reference rule covers {case.get('case_id')}")


def _validate_case(case):
    derived = _derive_expected(case)
    expected = case.get("expected", {})
    return {
        key: (expected.get(key), required_value)
        for key, required_value in derived.items()
        if expected.get(key) != required_value
    }


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

    def test_adversarial_eval_suite_is_executable_against_reference_semantics(self):
        ids = {case["case_id"] for case in self.evals["cases"]}
        required_ids = {
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
        self.assertTrue(required_ids <= ids)
        self.assertEqual(self.evals["boundary"], "SYNTHETIC_PUBLIC_SAFE / NO_RUNTIME_AUTHORIZATION / NO_TRADE")
        for case in self.evals["cases"]:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(_validate_case(case), {})

    def test_mutation_scope_forbidden_cannot_flip_projection_authorized(self):
        case = deepcopy(next(case for case in self.evals["cases"] if case["case_id"] == "EKM-EVAL-012-SCOPE-FORBIDDEN"))
        case["expected"]["projection_authorized"] = True
        self.assertEqual(_validate_case(case)["projection_authorized"], (True, False))

    def test_mutation_sensitive_profile_cannot_flip_authorized(self):
        case = deepcopy(next(case for case in self.evals["cases"] if case["case_id"] == "EKM-EVAL-013-SENSITIVE-PROFILE-INFERENCE"))
        case["expected"]["authorized"] = True
        self.assertEqual(_validate_case(case)["authorized"], (True, False))

    def test_mutation_caller_threshold_cannot_flip_cognitive_authorization(self):
        case = deepcopy(next(case for case in self.evals["cases"] if case["case_id"] == "EKM-EVAL-014-CALLER-CONTROLLED-THRESHOLD"))
        case["expected"]["cognitive_band_authorized"] = True
        self.assertEqual(_validate_case(case)["cognitive_band_authorized"], (True, False))


if __name__ == "__main__":
    unittest.main()
