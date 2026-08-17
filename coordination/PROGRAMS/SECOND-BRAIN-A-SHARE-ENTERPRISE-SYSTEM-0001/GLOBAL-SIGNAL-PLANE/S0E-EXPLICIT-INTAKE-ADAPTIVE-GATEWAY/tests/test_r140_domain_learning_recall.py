import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from global_signal_gateway import (
    DomainLearningRecallProvider,
    DomainLearningRecallRequest,
    GatewayError,
    ai_film_domain_learning_recall_read_only_smoke,
    route_domain_learning_recall,
    verify_recall_bundle,
    verify_recall_receipt,
    verify_recall_request,
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
    }
    value.update(changes)
    return value


class R140Matrix(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="r140-recall-")
        self.root = Path(self.temp.name)
        (self.root / "PROJECT_INDEX.yaml").write_text("project: public-fixture\n", encoding="utf-8")
        (self.root / "objects.txt").write_text("AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY golden_user_approved prompt_only\nCD25-KAIM-WINDOW-AB-20260815 candidate confounded_inconclusive\n", encoding="utf-8")
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
                                     paths=("PROJECT_INDEX.yaml", "objects.txt"), execution_id=execution_id)

    def _recall(self, *, item=None, request=None, execution_id="r140-test"):
        return DomainLearningRecallProvider().recall(request or self.request,
            authority_metadata=(item or authority(self.sha),), exact_read_proofs=self._proofs(execution_id), execution_id=execution_id)

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
            DomainLearningRecallProvider().recall(self.request, authority_metadata=(authority(self.sha),), exact_read_proofs=(), execution_id="r140-test")

    def test_r006_plain_dictionary_is_not_an_exact_proof(self):
        with self.assertRaisesRegex(GatewayError, "EXACT_PROOF_REQUIRED"):
            DomainLearningRecallProvider().recall(self.request, authority_metadata=(authority(self.sha),), exact_read_proofs=[self._proofs()[0].public_dict()], execution_id="r140-test")

    def test_r007_stale_domain_revision_fails_closed(self):
        with self.assertRaisesRegex(GatewayError, "STALE_DOMAIN_REVISION"):
            self._recall(item=authority("other"))

    def test_r008_proof_binding_mismatch_fails_closed(self):
        with self.assertRaisesRegex(GatewayError, "EXACT_PROOF_BINDING_MISMATCH"):
            DomainLearningRecallProvider().recall(self.request, authority_metadata=(authority(self.sha),), exact_read_proofs=self._proofs("other"), execution_id="r140-test")

    def test_r009_structural_multiaxis_positive_recall(self):
        bundle, receipt = self._recall()
        self.assertEqual((bundle.data["applicability_state"], receipt.data["decision"]), ("RECALLED", "RECALLED"))

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
        bundle, _receipt = self._recall()
        self.assertTrue(verify_recall_bundle(bundle, self.request))
        self.assertFalse(verify_recall_bundle(replace(bundle, bundle_digest="0" * 64), self.request))

    def test_r019_receipt_digest_and_bundle_binding(self):
        bundle, receipt = self._recall()
        self.assertTrue(verify_recall_receipt(receipt, self.request, bundle))
        self.assertFalse(verify_recall_receipt(replace(receipt, receipt_digest="0" * 64), self.request, bundle))

    def test_r020_process_is_not_creative_outcome(self):
        _bundle, receipt = self._recall()
        self.assertEqual(receipt.data["process_compliance"], "PASS")
        self.assertIn("RECALL_IS_NOT_CREATIVE_OUTCOME_PROOF", receipt.data["limitations"])

    def test_r021_no_domain_write_route(self):
        route = route_domain_learning_recall(self.request)
        self.assertFalse(route["domain_write_authorized"])
        self.assertFalse(route["formal_skill_promotion_authorized"])

    def test_r022_no_generic_cross_repo_writer(self):
        self.assertFalse(route_domain_learning_recall(self.request)["generic_cross_repo_writer_authorized"])

    def test_r023_no_object_yields_unsupported(self):
        bundle, receipt = DomainLearningRecallProvider().recall(self.request, authority_metadata=(), exact_read_proofs=self._proofs(), execution_id="r140-test")
        self.assertEqual((bundle.data["applicability_state"], receipt.data["decision"]), ("UNSUPPORTED", "UNSUPPORTED"))

    def test_r024_cd25_confounded_case_is_not_superiority(self):
        item = authority(self.sha, object_id="CD25-KAIM-WINDOW-AB-20260815", problem_signatures=["cd25"],
                         scene_classes=["cd25-window"], maturity="candidate", revalidation_state="NEEDS_REVALIDATION")
        request = DomainLearningRecallRequest.build(request_payload(domain_source_revision=self.sha, request_id="cd25", problem_signatures=["cd25"], scene_or_work_item="cd25-window"))
        bundle, receipt = self._recall(item=item, request=request)
        self.assertEqual(receipt.data["decision"], "NEEDS_REVALIDATION")
        self.assertEqual(bundle.data["maturity_observations"][0]["observed"], "candidate")

    def test_r025_exact_read_only_smoke_positive(self):
        result = ai_film_domain_learning_recall_read_only_smoke(self.root, self.request, object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY", metadata=authority(self.sha), source_path="objects.txt", required_evidence_markers=("golden_user_approved", "prompt_only"))
        self.assertEqual(result["receipt"]["decision"], "RECALLED")

    def test_r026_exact_read_only_smoke_zero_mutation(self):
        before = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.root, text=True)
        ai_film_domain_learning_recall_read_only_smoke(self.root, self.request, object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY", metadata=authority(self.sha), source_path="objects.txt")
        self.assertEqual(subprocess.check_output(["git", "status", "--porcelain"], cwd=self.root, text=True), before)

    def test_r027_missing_object_marker_fails_closed(self):
        with self.assertRaisesRegex(GatewayError, "DOMAIN_OBJECT_UNRESOLVED"):
            ai_film_domain_learning_recall_read_only_smoke(self.root, self.request, object_id="not-present", metadata=authority(self.sha), source_path="objects.txt")

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
            ai_film_domain_learning_recall_read_only_smoke(self.root, self.request, object_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY", metadata=authority(self.sha), source_path="objects.txt")


if __name__ == "__main__":
    unittest.main()
