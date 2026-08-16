import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from global_signal_gateway import (
    DomainLearningHandoffLedger,
    DomainLearningHandoffPacket,
    GatewayError,
    ai_film_domain_learning_read_only_smoke,
    require_exact_domain_revision,
    route_domain_learning_handoff,
    route_packet,
    stage_a_receipt,
    verify_packet,
    verify_receipt,
)


def payload(**changes):
    value = {
        "schema_version": "DomainLearningHandoffPacket/v1", "handoff_id": "h-1", "idempotency_key": "idem-1",
        "source_trace_ref": "trace:1", "source_scope": "PUBLIC_SAFE", "source_ref": "opaque://source/1",
        "observed_at": "2026-08-16T00:00:00+00:00", "domain_id": "AI_FILM",
        "domain_repository": "vxz2datoubo/eustia-ai-film", "domain_source_revision": "44c383afd2207a97caf45b1b0da6ee1dece43a76",
        "feedback_kind": "EXPLICIT_EXCELLENT_CASE", "user_intent": "reuse", "user_verdict": "POSITIVE",
        "work_item_id": "fashion-runway", "model_or_tool": "model", "model_version": "v1",
        "prompt_or_input_evidence_refs": ["opaque://input/1"], "result_evidence_refs": ["opaque://result/1"],
        "asset_refs": [], "observed_effects": ["preferred"], "candidate_goal": "classify",
        "privacy_class": "PUBLIC_SAFE", "public_safe_summary": "excellent case", "confidence_of_source_interpretation": "HIGH",
        "requested_domain_action": "LEARNING_CANDIDATE", "materiality": "TRACE_ONLY", "risk_flags": [], "unknowns": [],
    }
    value.update(changes)
    return value


class R139Matrix(unittest.TestCase):
    def packet(self, **changes):
        return DomainLearningHandoffPacket.build(payload(**changes))

    def _source_fixture(self):
        temp = tempfile.TemporaryDirectory(prefix="r139-readonly-")
        root = Path(temp.name)
        paths = {
            "PROJECT_INDEX.yaml": "project: test\n",
            "10_\u8fd0\u884c\u65f6/read_sets.yaml": """read_sets:
  golden_prompt_ingestion:
    always: [PROJECT_INDEX.yaml, \"\u4f18\u79c0\u63d0\u793a\u8bcd\u6848\u4f8b\u5b66\u4e60\u534f\u8bae\", golden_case_director_pull_schema, \"\u53cd\u9988\u53cd\u63a8\u4e0e\u7cfb\u7edf\u53cd\u54fa\u5f15\u64ce\", maturity_model, \"\u4f18\u79c0\u63d0\u793a\u8bcd\u6848\u4f8b\u5e93\"]
    conditional: {}
  system_research:
    always: [PROJECT_INDEX.yaml, \"AI\u7535\u5f71\u7cfb\u7edf\", \"\u53cd\u9988\u53cd\u63a8\u4e0e\u7cfb\u7edf\u53cd\u54fa\u5f15\u64ce\", \"\u5b98\u65b9\u8d44\u6599\u4e0e\u8bc1\u636e\u7d22\u5f15\", UNKNOWN_REGISTRY]
    conditional:
      model_real_generation_feedback: \"C-DANCE2.5\u771f\u5b9e\u751f\u6210\u53cd\u9988\u5e93\"
""",
            "08_\u7cfb\u7edf\u5b66\u4e60/\u4f18\u79c0\u63d0\u793a\u8bcd\u6848\u4f8b\u5b66\u4e60\u534f\u8bae.md": "protocol\n",
            "08_\u7cfb\u7edf\u5b66\u4e60/\u53cd\u9988\u53cd\u63a8\u4e0e\u7cfb\u7edf\u53cd\u54fa\u5f15\u64ce.md": "feedback\n",
            "09_\u8d44\u6599\u8bc1\u636e/\u5b98\u65b9\u8d44\u6599\u4e0e\u8bc1\u636e\u7d22\u5f15.md": "evidence\n",
            "10_\u8fd0\u884c\u65f6/golden_case_director_pull_schema.yaml": "schema: 1\n",
            "10_\u8fd0\u884c\u65f6/maturity_model.yaml": "maturity: candidate\n",
            "11_\u9a8c\u6536/golden_prompt_cases.yaml": "- id: GPC-20260813-001\n  status: golden_user_approved\n  verdict_basis: prompt_only\n",
            "12_\u672a\u77e5\u9879/UNKNOWN_REGISTRY.yaml": "unknowns: []\n",
            "01_AI\u7535\u5f71\u7cfb\u7edf/AI\u7535\u5f71\u7cfb\u7edf.md": "film\n",
            "08_\u7cfb\u7edf\u5b66\u4e60/C-DANCE2.5\u771f\u5b9e\u751f\u6210\u53cd\u9988\u5e93.md": "CD25-KAIM-WINDOW-AB-20260815 candidate confounded_inconclusive\n",
        }
        for rel, body in paths.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "r139@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "R139 Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        return temp, root, sha

    def test_r001_excellent_case_packet(self):
        self.assertTrue(verify_packet(self.packet()))

    def test_r002_positive_negative_verdict_distinct(self):
        self.assertNotEqual(self.packet().packet_digest, self.packet(user_verdict="NEGATIVE").packet_digest)

    def test_r003_generation_version_provenance(self):
        packet = self.packet(feedback_kind="REAL_GENERATION_EVIDENCE", model_or_tool="C-DANCE2.5", model_version="2.5")
        self.assertEqual((packet.data["model_or_tool"], packet.data["model_version"]), ("C-DANCE2.5", "2.5"))

    def test_r004_routine_feedback_is_trace_only(self):
        route = route_packet(self.packet())
        self.assertEqual((route["persistence_class"], route["execution_class"]), ("TRACE_ONLY", "DOMAIN_WORKFLOW"))

    def test_r005_material_effect_is_durable_signal(self):
        route = route_packet(self.packet(materiality="DURABLE_SIGNAL"))
        self.assertEqual((route["persistence_class"], route["execution_class"]), ("DURABLE_SIGNAL", "GOVERNED_MISSION"))

    def test_r006_exact_duplicate_suppressed(self):
        ledger = DomainLearningHandoffLedger()
        self.assertEqual(ledger.ingest(self.packet())["status"], "ROUTED")
        self.assertEqual(ledger.ingest(self.packet())["status"], "DUPLICATE")

    def test_r007_correction_is_append_only(self):
        ledger = DomainLearningHandoffLedger()
        original = ledger.ingest(self.packet())
        correction = self.packet(handoff_id="h-2", idempotency_key="idem-2", user_verdict="NEGATIVE")
        result = ledger.correct(original["packet_ref"], correction, "CONTRADICTS")
        self.assertTrue(result["history_preserved"])
        self.assertEqual(ledger.relations()[0]["relation"], "CONTRADICTS")

    def test_r008_stale_domain_head_fails_closed(self):
        with self.assertRaisesRegex(GatewayError, "STALE_DOMAIN_REVISION"):
            require_exact_domain_revision(self.packet(), "other")

    def test_r009_unsupported_processor_is_unknown(self):
        receipt = stage_a_receipt(self.packet())
        self.assertEqual((receipt.data["processor_capability_id"], receipt.data["process_compliance"]), ("UNKNOWN", "UNVERIFIED"))

    def test_r010_dry_run_cannot_claim_writeback(self):
        self.assertEqual(stage_a_receipt(self.packet()).data["writeback_status"], "NONE")

    def test_r011_no_second_ai_film_truth(self):
        self.assertNotIn("domain_classification", self.packet().data)
        self.assertEqual(stage_a_receipt(self.packet()).data["domain_classification"], "UNKNOWN")

    def test_r012_maturity_is_domain_owned(self):
        self.assertFalse(route_packet(self.packet())["domain_maturity_authorized"])

    def test_r013_one_success_does_not_promote(self):
        route = route_packet(self.packet())
        self.assertFalse(route["formal_task_authorized"])
        self.assertFalse(route["domain_write_authorized"])

    def test_r014_confounded_ab_stays_inconclusive(self):
        receipt = stage_a_receipt(self.packet(feedback_kind="REAL_GENERATION_EVIDENCE"))
        self.assertEqual((receipt.data["process_compliance"], receipt.data["outcome_quality"]), ("UNVERIFIED", "NOT_YET_OBSERVED"))

    def test_r015_packet_digest_covers_trusted_fields(self):
        packet = self.packet()
        self.assertFalse(verify_packet(replace(packet, packet_digest="0" * 64)))
        self.assertNotEqual(packet.packet_digest, self.packet(public_safe_summary="changed").packet_digest)

    def test_r016_receipt_digest_and_packet_binding(self):
        packet, receipt = self.packet(), stage_a_receipt(self.packet())
        self.assertFalse(verify_receipt(replace(receipt, receipt_digest="0" * 64), packet))
        self.assertTrue(verify_receipt(receipt, packet))
        self.assertFalse(verify_receipt(receipt, self.packet(handoff_id="other", idempotency_key="other")))

    def test_r017_private_body_is_rejected(self):
        with self.assertRaisesRegex(GatewayError, "PRIVATE_OR_SECRET"):
            self.packet(raw_private_body="private")

    def test_r018_secret_is_rejected(self):
        with self.assertRaisesRegex(GatewayError, "PRIVATE_OR_SECRET"):
            self.packet(public_safe_summary="sk" + "-secret")

    def test_r019_exact_domain_revision_binding(self):
        packet = self.packet()
        require_exact_domain_revision(packet, packet.data["domain_source_revision"])

    def test_r020_process_and_outcome_are_separate(self):
        receipt = stage_a_receipt(self.packet())
        self.assertNotEqual(receipt.data["process_compliance"], receipt.data["outcome_quality"])

    def test_r021_unrelated_scan_is_not_satisfied(self):
        self.assertNotIn("actual_scans", route_packet(self.packet()))

    def test_r022_r138_is_not_a_domain_writer(self):
        self.assertFalse(route_domain_learning_handoff(self.packet())["domain_write_authorized"])

    def test_r023_idempotency_collision_fails_closed(self):
        ledger = DomainLearningHandoffLedger()
        ledger.ingest(self.packet())
        with self.assertRaisesRegex(GatewayError, "IDEMPOTENCY_COLLISION"):
            ledger.ingest(self.packet(handoff_id="other"))

    def test_r024_omission_is_not_revocation(self):
        ledger = DomainLearningHandoffLedger()
        original = ledger.ingest(self.packet())
        self.assertEqual(original["status"], "ROUTED")
        self.assertEqual(ledger.relations(), ())

    def test_r025_retrieval_metadata_has_scope_and_failures(self):
        route = route_packet(self.packet(applicable_context=["runway"], failure_conditions=["model-version-drift"], needs_revalidation=True))
        self.assertEqual(route["retrieval_metadata"]["revalidation_state"], "NEEDS_REVALIDATION")
        self.assertEqual(route["retrieval_metadata"]["failure_conditions"], ("model-version-drift",))

    def test_r026_model_version_revalidation_guard(self):
        self.assertNotEqual(self.packet(model_version="v1").packet_digest, self.packet(model_version="v2").packet_digest)

    def test_r027_excellent_case_read_set_smoke(self):
        temp, root, sha = self._source_fixture()
        try:
            packet = self.packet(domain_source_revision=sha, work_item_id="AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY")
            with patch("global_signal_gateway.domain_learning_handoff.AI_FILM_COMMIT", sha), patch("global_signal_gateway.domain_learning_handoff.AI_FILM_REPOSITORY", "vxz2datoubo/eustia-ai-film"):
                result = ai_film_domain_learning_read_only_smoke(root, packet, read_set="golden_prompt_ingestion", exact_object="GPC-20260813-001")
            self.assertEqual(result["director_route_requirement"], "NOT_REQUIRED_FOR_THIS_READ_SET_SMOKE")
            self.assertEqual(result["observed_evidence_constraints"]["verdict_basis"], "prompt_only")
        finally:
            temp.cleanup()

    def test_r028_cd25_real_feedback_read_set_smoke(self):
        temp, root, sha = self._source_fixture()
        try:
            packet = self.packet(domain_source_revision=sha, work_item_id="CD25-KAIM-WINDOW-AB-20260815", feedback_kind="REAL_GENERATION_EVIDENCE")
            with patch("global_signal_gateway.domain_learning_handoff.AI_FILM_COMMIT", sha), patch("global_signal_gateway.domain_learning_handoff.AI_FILM_REPOSITORY", "vxz2datoubo/eustia-ai-film"):
                result = ai_film_domain_learning_read_only_smoke(root, packet, read_set="system_research", exact_object="CD25-KAIM-WINDOW-AB-20260815", conditional_flags={"model_real_generation_feedback": True})
            self.assertEqual(result["receipt_candidate"]["outcome_quality"], "NOT_YET_OBSERVED")
            self.assertEqual(result["observed_evidence_constraints"]["soac_comparison_result"], "confounded_inconclusive")
        finally:
            temp.cleanup()

    def test_r029_zero_ai_film_mutation(self):
        temp, root, sha = self._source_fixture()
        try:
            before = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True)
            packet = self.packet(domain_source_revision=sha)
            with patch("global_signal_gateway.domain_learning_handoff.AI_FILM_COMMIT", sha):
                ai_film_domain_learning_read_only_smoke(root, packet, read_set="golden_prompt_ingestion", exact_object="GPC-20260813-001")
            self.assertEqual(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True), before)
        finally:
            temp.cleanup()

    def test_r030_resource_bounded_clean(self):
        temp, root, _sha = self._source_fixture()
        path = Path(temp.name)
        self.assertTrue(root.exists())
        temp.cleanup()
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
