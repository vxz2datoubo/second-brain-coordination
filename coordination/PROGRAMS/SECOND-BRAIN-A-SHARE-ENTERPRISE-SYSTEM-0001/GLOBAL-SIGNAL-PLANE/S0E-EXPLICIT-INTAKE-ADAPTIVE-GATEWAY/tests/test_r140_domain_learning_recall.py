import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from global_signal_gateway import (
    DomainLearningRecallBundle,
    DomainLearningRecallReceipt,
    DomainAuthorityProjection,
    DomainLearningRecallProvider,
    DomainLearningRecallRequest,
    GatewayError,
    ai_film_domain_learning_recall_read_only_smoke,
    route_domain_learning_recall,
    verify_recall_bundle,
    verify_recall_receipt,
    verify_recall_authority_projection,
    validate_recall_authority_projection_structure,
    verify_recall_request,
    validate_recall_bundle_structure,
    validate_recall_receipt_structure,
)
from global_signal_gateway.gateway import exact_git_read_proofs


def request_payload(**changes):
    value = {
        "schema_version": "DomainLearningRecallRequest/v1", "request_id": "r140-request-1",
        "source_trace_ref": "opaque://trace/r140-1", "domain_id": "AI_FILM",
        "domain_repository": "vxz2datoubo/eustia-ai-film", "domain_source_revision": "pending",
        "problem_signatures": ["fashion", "runway", "hard-dual-light"], "scene_or_work_item": "fashion-runway",
        "model_or_tool": "C-DANCE", "model_version": "2.5", "constraints": ["black-void"],
        "requested_evidence_classes": ["public-case", "maturity"], "privacy_class": "PUBLIC_SAFE",
        "observed_at": "2026-08-17T00:00:00+00:00",
    }
    value.update(changes)
    return value


def authority(revision, **changes):
    value = {
        "object_id": "AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY", "source_ref": "opaque://ai-film/golden/1",
        "domain_source_revision": revision, "problem_signatures": ["fashion", "runway", "hard-dual-light"],
        "scene_classes": ["fashion-runway"], "model_or_tool": "C-DANCE", "model_versions": ["2.5"],
        "constraints": ["black-void"], "maturity": "golden_user_approved_prompt_only",
        "applicability": ["black-void"], "non_applicability": [], "failure_conditions": [], "counterexamples": [],
        "revalidation_state": "CURRENT", "evidence_refs": ["opaque://ai-film/evidence/1"],
        "authority_unknowns": [],
    }
    value.update(changes)
    return value


class R140Matrix(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="r140-recall-")
        self.root = Path(self.temp.name)
        (self.root / "PROJECT_INDEX.yaml").write_text("project: public-fixture\n", encoding="utf-8")
        golden = self.root / "11_\u9a8c\u6536" / "golden_prompt_cases.yaml"
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text("""cases:
  - case_id: GPC-20260813-001
    task_class: high_end_fashion_commercial_kinetic_typography
    model_or_tool_dependency: {status: unknown}
    applicable_context: [runway_style_ad]
    non_applicable_context: [dialogue_driven_scene]
    failure_boundaries: [topology_heavy_story_scene]
    revalidation_triggers: [model_or_version_change]
    case_status: golden_user_approved
    verdict_scope: prompt_approved
    verdict_basis: prompt_only
""", encoding="utf-8")
        regression = self.root / "11_\u9a8c\u6536" / "director_regression_cases.yaml"
        regression.write_text("""cases:
  - id: REG-CDANCE25-TEMPORAL-EXCLUSIVITY-001
    maturity: candidate
    scene_evidence:
      experiment_id: CD25-KAIM-WINDOW-AB-20260815
      work_item: KAIM-HIGH-SEARCH-30S / 7s window micro-sequence
      evidence_status: scene_verified_observation_reusable_strategy_unvalidated
""", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "r140@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "R140 Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)
        self.sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        self.request = DomainLearningRecallRequest.build(request_payload(domain_source_revision=self.sha))

    def tearDown(self):
        self.temp.cleanup()

    def _proofs(self, execution_id="r140-test"):
        return exact_git_read_proofs(self.root, repository="vxz2datoubo/eustia-ai-film", commit=self.sha,
                                     paths=("PROJECT_INDEX.yaml", "11_\u9a8c\u6536/golden_prompt_cases.yaml"), execution_id=execution_id)

    def _recall(self, *, item=None, request=None, execution_id="r140-test"):
        return DomainLearningRecallProvider().recall_structural(request or self.request,
            authority_metadata=(item or authority(self.sha),), exact_read_proofs=self._proofs(execution_id), execution_id=execution_id)

    def _trusted_recall(self, *, request=None, execution_id="r140-trusted"):
        trusted_request = request or self._fashion_request()
        provider = DomainLearningRecallProvider()
        projection = provider.project_ai_film_authority(self.root, trusted_request,
                                                        object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY",
                                                        execution_id=execution_id)
        self.assertTrue(verify_recall_authority_projection(projection, trusted_request, execution_id=execution_id))
        return provider.recall(trusted_request, authority_projections=(projection,), exact_read_proofs=projection._proofs,
                               execution_id=execution_id), trusted_request

    def _fashion_request(self, **changes):
        value = request_payload(domain_source_revision=self.sha, request_id="fashion", problem_signatures=["high_end_fashion_commercial_kinetic_typography"], scene_or_work_item="runway_style_ad", model_or_tool="UNKNOWN", model_version="UNKNOWN", constraints=["runway_style_ad"])
        value.update(changes)
        return DomainLearningRecallRequest.build(value)

    def test_r001_request_schema_and_digest(self):
        self.assertTrue(verify_recall_request(self.request))

    def test_r002_request_timestamp_must_be_aware(self):
        with self.assertRaisesRegex(GatewayError, "NAIVE_TIMESTAMP"):
            DomainLearningRecallRequest.build(request_payload(domain_source_revision=self.sha, observed_at="2026-08-17T00:00:00"))

    def test_r003_request_public_safety(self):
        with self.assertRaisesRegex(GatewayError, "PRIVATE_OR_SECRET"):
            DomainLearningRecallRequest.build(request_payload(domain_source_revision=self.sha, source_trace_ref="sk" + "-secret"))
        with self.assertRaisesRegex(GatewayError, "SECRET_SCOPE"):
            DomainLearningRecallRequest.build(request_payload(domain_source_revision=self.sha, privacy_class="SECRET_CREDENTIAL"))

    def test_r004_request_digest_tamper_rejected(self):
        self.assertFalse(verify_recall_request(replace(self.request, request_digest="0" * 64)))

    def test_r005_exact_read_proof_is_required(self):
        with self.assertRaisesRegex(GatewayError, "EXACT_PROOF_REQUIRED"):
            DomainLearningRecallProvider().recall_structural(self.request, authority_metadata=(authority(self.sha),), exact_read_proofs=(), execution_id="r140-test")

    def test_r006_plain_dictionary_is_not_an_exact_proof(self):
        with self.assertRaisesRegex(GatewayError, "EXACT_PROOF_REQUIRED"):
            DomainLearningRecallProvider().recall_structural(self.request, authority_metadata=(authority(self.sha),), exact_read_proofs=[self._proofs()[0].public_dict()], execution_id="r140-test")

    def test_r007_stale_domain_revision_fails_closed(self):
        with self.assertRaisesRegex(GatewayError, "STALE_DOMAIN_REVISION"):
            self._recall(item=authority("other"))

    def test_r008_proof_binding_mismatch_fails_closed(self):
        with self.assertRaisesRegex(GatewayError, "EXACT_PROOF_BINDING_MISMATCH"):
            DomainLearningRecallProvider().recall_structural(self.request, authority_metadata=(authority(self.sha),), exact_read_proofs=self._proofs("other"), execution_id="r140-test")

    def test_r009_structural_multiaxis_positive_recall(self):
        # A genuine exact proof plus caller-authored favorable metadata is a
        # structural preview only; it must never acquire trusted issuance.
        bundle, receipt = self._recall()
        self.assertEqual((bundle.data["applicability_state"], receipt.data["decision"]), ("RECALLED", "RECALLED"))
        self.assertFalse(verify_recall_bundle(bundle, self.request))
        self.assertFalse(verify_recall_receipt(receipt, self.request, bundle))
        with self.assertRaises(TypeError):
            DomainLearningRecallProvider().recall(self.request, authority_metadata=(authority(self.sha),),
                                                   exact_read_proofs=self._proofs(), execution_id="r140-test")
        trusted_request = self._fashion_request()
        provider = DomainLearningRecallProvider()
        projection = provider.project_ai_film_authority(self.root, trusted_request,
                                                        object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY",
                                                        execution_id="r140-projection")
        caller_projection = DomainAuthorityProjection.build(projection.public_dict())
        self.assertTrue(validate_recall_authority_projection_structure(caller_projection))
        self.assertFalse(verify_recall_authority_projection(caller_projection, trusted_request, execution_id="r140-projection"))
        with self.assertRaisesRegex(GatewayError, "PROJECTION_REQUIRED"):
            provider.recall(trusted_request, authority_projections=(caller_projection,), exact_read_proofs=projection._proofs,
                            execution_id="r140-projection")

    def test_r010_text_like_but_scene_mismatch_abstains(self):
        bundle, receipt = self._recall(item=authority(self.sha, scene_classes=["other-scene"]))
        self.assertEqual(receipt.data["decision"], "ABSTAINED")
        self.assertIn("STRUCTURAL_MATCH_INSUFFICIENT", bundle.data["abstentions"])

    def test_r011_model_version_mismatch_requires_revalidation(self):
        bundle, receipt = self._recall(item=authority(self.sha, model_versions=["3.0"]))
        self.assertEqual((bundle.data["applicability_state"], receipt.data["decision"]), ("NEEDS_REVALIDATION", "NEEDS_REVALIDATION"))

    def test_r012_failure_condition_cannot_positive_recall(self):
        bundle, receipt = self._recall(item=authority(self.sha, failure_conditions=["black-void"]))
        self.assertEqual(receipt.data["decision"], "CONFLICTED")
        self.assertEqual(bundle.data["failure_condition_hits"], ("black-void",))

    def test_r013_counterexample_cannot_positive_recall(self):
        bundle, receipt = self._recall(item=authority(self.sha, counterexamples=["fashion"]))
        self.assertEqual(receipt.data["decision"], "CONFLICTED")
        self.assertEqual(bundle.data["counterexample_hits"], ("fashion",))

    def test_r014_conflicted_domain_state_is_preserved(self):
        _bundle, receipt = self._recall(item=authority(self.sha, revalidation_state="CONFLICTED"))
        self.assertEqual(receipt.data["decision"], "CONFLICTED")

    def test_r015_needs_revalidation_is_preserved(self):
        _bundle, receipt = self._recall(item=authority(self.sha, revalidation_state="NEEDS_REVALIDATION"))
        self.assertEqual(receipt.data["decision"], "NEEDS_REVALIDATION")

    def test_r016_missing_authority_metadata_fails_closed(self):
        item = authority(self.sha); item.pop("maturity")
        with self.assertRaisesRegex(GatewayError, "METADATA_MISSING"):
            self._recall(item=item)

    def test_r017_domain_lesson_body_cannot_enter_metadata(self):
        with self.assertRaisesRegex(GatewayError, "LESSON_BODY_OR_SECRET"):
            self._recall(item=authority(self.sha, lesson_body="copy forbidden"))

    def test_r018_bundle_digest_and_request_binding(self):
        (bundle, _receipt), trusted_request = self._trusted_recall()
        self.assertTrue(verify_recall_bundle(bundle, trusted_request))
        self.assertFalse(verify_recall_bundle(replace(bundle, bundle_digest="0" * 64), trusted_request))
        caller_bundle = DomainLearningRecallBundle.build(bundle.public_dict())
        self.assertTrue(validate_recall_bundle_structure(caller_bundle, trusted_request))
        self.assertFalse(verify_recall_bundle(caller_bundle, trusted_request))

    def test_r019_receipt_digest_and_bundle_binding(self):
        (bundle, receipt), trusted_request = self._trusted_recall()
        self.assertTrue(verify_recall_receipt(receipt, trusted_request, bundle))
        self.assertFalse(verify_recall_receipt(replace(receipt, receipt_digest="0" * 64), trusted_request, bundle))
        caller_receipt = DomainLearningRecallReceipt.build(receipt.public_dict())
        self.assertTrue(validate_recall_receipt_structure(caller_receipt, trusted_request, bundle))
        self.assertFalse(verify_recall_receipt(caller_receipt, trusted_request, bundle))

    def test_r020_process_is_not_creative_outcome(self):
        (_bundle, receipt), _trusted_request = self._trusted_recall()
        self.assertEqual(receipt.data["process_compliance"], "PASS")
        self.assertIn("RECALL_IS_NOT_CREATIVE_OUTCOME_PROOF", receipt.data["limitations"])

    def test_r021_no_domain_write_route(self):
        route = route_domain_learning_recall(self.request)
        self.assertFalse(route["domain_write_authorized"])
        self.assertFalse(route["formal_skill_promotion_authorized"])

    def test_r022_no_generic_cross_repo_writer(self):
        self.assertFalse(route_domain_learning_recall(self.request)["generic_cross_repo_writer_authorized"])

    def test_r023_empty_projection_is_not_authority_resolution_evidence(self):
        # This fixture contains a matching golden object and genuine exact
        # proofs.  Empty caller input must not turn that absence into a trusted
        # UNSUPPORTED/PASS receipt.
        request = self._fashion_request()
        proofs = exact_git_read_proofs(self.root, repository="vxz2datoubo/eustia-ai-film", commit=self.sha,
                                       paths=("PROJECT_INDEX.yaml", "11_验收/golden_prompt_cases.yaml"),
                                       execution_id="r140-empty-projection")
        with self.assertRaisesRegex(GatewayError, "AUTHORITY_RESOLUTION_INCOMPLETE"):
            DomainLearningRecallProvider().recall(request, authority_projections=(), exact_read_proofs=proofs,
                                                   execution_id="r140-empty-projection")

    def test_r024_cd25_confounded_case_is_not_superiority(self):
        request = DomainLearningRecallRequest.build(request_payload(domain_source_revision=self.sha, request_id="cd25", problem_signatures=["KAIM-HIGH-SEARCH-30S / 7s window micro-sequence"], scene_or_work_item="KAIM-HIGH-SEARCH-30S / 7s window micro-sequence", model_or_tool="UNKNOWN", model_version="UNKNOWN", constraints=[]))
        result = ai_film_domain_learning_recall_read_only_smoke(self.root, request, object_id="CD25-KAIM-WINDOW-AB-20260815")
        bundle, receipt = result["bundle"], result["receipt"]
        self.assertEqual(receipt["decision"], "NEEDS_REVALIDATION")
        self.assertEqual(bundle["maturity_observations"][0]["observed"], "candidate")

    def test_r025_exact_read_only_smoke_positive(self):
        request = self._fashion_request()
        result = ai_film_domain_learning_recall_read_only_smoke(self.root, request, object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY")
        self.assertEqual(result["receipt"]["decision"], "NEEDS_REVALIDATION")
        self.assertEqual(result["authority_projection"], "DOMAIN_OWNED_EXACT_STRUCTURED_PROJECTION")
        with self.assertRaises(TypeError):
            ai_film_domain_learning_recall_read_only_smoke(self.root, request, object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY", metadata=authority(self.sha))

    def test_r026_exact_read_only_smoke_zero_mutation(self):
        before = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.root, text=True)
        ai_film_domain_learning_recall_read_only_smoke(self.root, self._fashion_request(), object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY")
        self.assertEqual(subprocess.check_output(["git", "status", "--porcelain"], cwd=self.root, text=True), before)

    def test_r027_missing_object_marker_fails_closed(self):
        with self.assertRaisesRegex(GatewayError, "DOMAIN_OBJECT_UNRESOLVED"):
            ai_film_domain_learning_recall_read_only_smoke(self.root, self.request, object_id="not-present")

    def test_r028_incompatible_negative_replay(self):
        request = DomainLearningRecallRequest.build(request_payload(domain_source_revision=self.sha, model_version="9.9"))
        _bundle, receipt = self._recall(request=request)
        self.assertEqual(receipt.data["decision"], "NEEDS_REVALIDATION")

    def test_r029_opaque_ref_only_bundle(self):
        bundle, _receipt = self._recall()
        self.assertNotIn("lesson_body", bundle.public_dict())
        self.assertTrue(bundle.data["matched_object_refs"][0].startswith("domain-object:"))

    def test_r030_source_clean_required(self):
        (self.root / "untracked.txt").write_text("dirty", encoding="utf-8")
        with self.assertRaisesRegex(GatewayError, "AI_FILM_SOURCE_NOT_CLEAN"):
            ai_film_domain_learning_recall_read_only_smoke(self.root, self._fashion_request(), object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY")


if __name__ == "__main__":
    unittest.main()
