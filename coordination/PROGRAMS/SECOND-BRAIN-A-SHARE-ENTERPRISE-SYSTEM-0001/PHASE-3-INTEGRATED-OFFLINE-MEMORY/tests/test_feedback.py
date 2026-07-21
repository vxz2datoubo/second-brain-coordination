from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import unittest
from pathlib import Path


PHASE_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PHASE_ROOT.parent
for source_root in (
    PHASE_ROOT / "src",
    PROGRAM_ROOT / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src",
    PROGRAM_ROOT / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src",
):
    sys.path.insert(0, str(source_root))

from integrated_offline_memory.feedback import FeedbackProcessor, FeedbackRecord
from integrated_offline_memory.learning_packet import build_learning_packet
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan
from integrated_offline_memory.schema_validation import validate_schema_subset
from integrated_offline_memory.security import CredentialValueDenied
from integrated_offline_memory.snapshot import SnapshotManager


def packet(statement: str, *, unknowns=None, manifest_id="feedback-source"):
    return build_learning_packet(
        source_manifest_ids=[manifest_id],
        source_hash="f" * 64,
        validation_report={"status": "SYNTHETIC_TEST", "research_only": True},
        evidence_refs=["manifest:" + manifest_id, "evidence:synthetic"],
        atoms=[{
            "atom_type": "fact",
            "statement": statement,
            "scope": "feedback-test",
            "confidence": 0.8,
        }],
        unknowns=unknowns or [],
    )


class FeedbackWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)
        self.processor = FeedbackProcessor(self.store)

    def _seed(self, statement="original statement"):
        value = packet(statement)
        self.store.import_learning_packet(value)
        return value["atoms"][0]["id"]

    def test_374_duplicate_preview_is_candidate_packet(self):
        target = self._seed()
        preview = self.processor.preview(FeedbackRecord("DUPLICATE", target_atom_ids=(target,)))
        self.assertEqual((preview.status, preview.authority_write, preview.no_trade_gate), ("candidate", False, True))
        self.assertEqual(preview.primary_atom_id, target)

    def test_375_supplement_preview_is_supported(self):
        preview = self.processor.preview(FeedbackRecord("SUPPLEMENT", statement="supplemental detail"))
        self.assertEqual(preview.feedback_type, "SUPPLEMENT")

    def test_376_refinement_creates_explicit_relation(self):
        target = self._seed()
        preview = self.processor.preview(FeedbackRecord("REFINEMENT", "refined statement", target_atom_ids=(target,)))
        self.assertEqual(preview.packet["relations"][0]["relation_type"], "refines")

    def test_377_conflict_creates_conflict_object(self):
        target = self._seed()
        preview = self.processor.preview(FeedbackRecord("CONFLICT", "opposing evidence", target_atom_ids=(target,)))
        self.assertEqual(preview.packet["conflicts"][0]["conflict_type"], "CONFLICT")

    def test_378_correction_does_not_silently_supersede(self):
        target = self._seed()
        preview = self.processor.preview(FeedbackRecord("CORRECTION", "candidate correction", target_atom_ids=(target,)))
        receipt = self.processor.commit(preview)
        self.assertEqual(self.store.get_atom(target)["knowledge_status"], "candidate")
        self.assertTrue(receipt.added_atom_ids)
        self.assertEqual(self.store.stats()["conflicts"], 1)

    def test_379_supersedes_changes_current_but_preserves_history(self):
        target = self._seed("obsolete formulation")
        preview = self.processor.preview(FeedbackRecord("SUPERSEDES", "replacement formulation", target_atom_ids=(target,)))
        self.processor.commit(preview)
        self.assertEqual(self.store.get_atom(target)["knowledge_status"], "superseded")
        current = ContextAssembler(self.store).assemble(QueryPlan(query_text="obsolete formulation"))
        self.assertNotIn(target, {atom["id"] for atom in current.atoms})
        history = ContextAssembler(self.store).assemble(QueryPlan(
            query_text="obsolete formulation",
            truth_states=("candidate", "approved", "conflict", "unknown", "superseded"),
            history_mode="HISTORY",
        ))
        self.assertIn(target, {atom["id"] for atom in history.atoms})

    def test_380_unknown_resolved_updates_unknown_status(self):
        base = packet("known context")
        target = base["atoms"][0]["id"]
        base = packet("known context", unknowns=[{
            "id": "unknown-feedback-test",
            "question": "what resolves this",
            "related_atom_ids": [target],
            "source_refs": ["evidence:synthetic"],
        }])
        self.store.import_learning_packet(base)
        preview = self.processor.preview(FeedbackRecord(
            "UNKNOWN_RESOLVED", "verified resolution candidate",
            target_unknown_ids=("unknown-feedback-test",),
        ))
        receipt = self.processor.commit(preview)
        self.assertEqual(self.store.get_unknown("unknown-feedback-test")["status"], "RESOLVED")
        self.assertEqual(receipt.resolved_unknown_ids, ("unknown-feedback-test",))

    def test_381_preview_has_no_store_mutation(self):
        target = self._seed()
        before = self.store.stats()
        self.processor.preview(FeedbackRecord("REFINEMENT", "preview only", target_atom_ids=(target,)))
        self.assertEqual(self.store.stats(), before)

    def test_382_commit_records_public_receipt(self):
        preview = self.processor.preview(FeedbackRecord("SUPPLEMENT", "committed addition"))
        receipt = self.processor.commit(preview)
        stored = self.store.get_feedback_receipt(receipt.feedback_id)
        self.assertEqual(stored["packet_id"], receipt.packet_id)
        self.assertEqual(self.store.stats()["feedback_receipts"], 1)

    def test_383_repeated_feedback_is_idempotent(self):
        record = FeedbackRecord("SUPPLEMENT", "same feedback twice")
        first = self.processor.commit(self.processor.preview(record))
        atoms_after_first = self.store.stats()["atoms"]
        second = self.processor.commit(self.processor.preview(record))
        self.assertEqual((first.packet_id, second.packet_id), (first.packet_id, first.packet_id))
        self.assertEqual(self.store.stats()["atoms"], atoms_after_first)
        self.assertEqual(self.store.stats()["feedback_receipts"], 1)

    def test_384_duplicate_does_not_inflate_atom_count(self):
        target = self._seed()
        count = self.store.stats()["atoms"]
        self.processor.commit(self.processor.preview(FeedbackRecord("DUPLICATE", target_atom_ids=(target,))))
        self.assertEqual(self.store.stats()["atoms"], count)

    def test_385_invalid_feedback_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "feedback_type_invalid"):
            FeedbackRecord("OTHER", "x").validate()

    def test_386_required_atom_target_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "atom_target_required"):
            FeedbackRecord("CORRECTION", "x").validate()

    def test_387_missing_atom_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "atom_target_missing"):
            self.processor.preview(FeedbackRecord("CONFLICT", "x", target_atom_ids=("missing",)))

    def test_388_missing_unknown_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown_target_missing"):
            self.processor.preview(FeedbackRecord("UNKNOWN_RESOLVED", "x", target_unknown_ids=("missing",)))

    def test_389_credential_shaped_feedback_is_denied(self):
        secret = "ghp_" + "A" * 32
        with self.assertRaises(CredentialValueDenied):
            FeedbackRecord("SUPPLEMENT", secret).validate()

    def test_390_preview_hash_tampering_is_rejected(self):
        preview = self.processor.preview(FeedbackRecord("SUPPLEMENT", "tamper guarded"))
        with self.assertRaisesRegex(ValueError, "preview_hash_mismatch"):
            self.processor.commit(dataclasses.replace(preview, preview_hash="0" * 64))

    def test_391_feedback_id_is_deterministic(self):
        record = FeedbackRecord("SUPPLEMENT", "deterministic feedback")
        self.assertEqual(record.feedback_id, record.feedback_id)

    def test_392_preview_hash_is_deterministic_without_mutation(self):
        record = FeedbackRecord("SUPPLEMENT", "deterministic preview")
        self.assertEqual(self.processor.preview(record).preview_hash, self.processor.preview(record).preview_hash)

    def test_393_commit_reports_positive_retrieval_effect(self):
        receipt = self.processor.commit(self.processor.preview(FeedbackRecord("SUPPLEMENT", "new searchable effect")))
        self.assertIn(receipt.added_atom_ids[0], receipt.after_atom_ids)

    def test_394_revocation_removes_source_from_current_results(self):
        manifest_id = "manifest-revoke-test"
        self.store.register_knowledge_source(
            manifest_id=manifest_id,
            manifest_hash="a" * 64,
            policy_id="policy-revoke",
            public_metadata={"source_kind": "SYNTHETIC_TEST"},
        )
        self.store.import_learning_packet(packet("revocable knowledge", manifest_id=manifest_id))
        receipt = self.processor.revoke_source(manifest_id, "user_revoked")
        self.assertTrue(receipt.changed)
        self.assertTrue(receipt.removed_current_atom_ids)
        self.assertEqual(receipt.removed_current_atom_ids, receipt.historical_atom_ids)

    def test_395_repeated_revocation_is_safe(self):
        manifest_id = "manifest-revoke-repeat"
        self.store.register_knowledge_source(
            manifest_id=manifest_id,
            manifest_hash="b" * 64,
            policy_id="policy-revoke",
            public_metadata={"source_kind": "SYNTHETIC_TEST"},
        )
        self.processor.revoke_source(manifest_id, "user_revoked")
        second = self.processor.revoke_source(manifest_id, "user_revoked")
        self.assertFalse(second.changed)
        self.assertEqual(second.previous_status, "REVOKED")

    def test_396_revocation_reason_free_text_is_rejected(self):
        self.store.register_knowledge_source(
            manifest_id="manifest-reason-test",
            manifest_hash="c" * 64,
            policy_id="policy-revoke",
            public_metadata={"source_kind": "SYNTHETIC_TEST"},
        )
        with self.assertRaisesRegex(ValueError, "reason_invalid"):
            self.processor.revoke_source("manifest-reason-test", "private free text")

    def test_397_feedback_learning_packet_schema_validates(self):
        preview = self.processor.preview(FeedbackRecord("SUPPLEMENT", "schema feedback"))
        schema = json.loads((PHASE_ROOT / "schemas" / "FeedbackLearningPacket.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, preview.to_dict())

    def test_398_feedback_commit_receipt_schema_validates(self):
        receipt = self.processor.commit(self.processor.preview(FeedbackRecord("SUPPLEMENT", "schema commit")))
        schema = json.loads((PHASE_ROOT / "schemas" / "FeedbackCommitReceipt.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, receipt.to_dict())

    def test_399_revocation_receipt_schema_validates(self):
        self.store.register_knowledge_source(
            manifest_id="manifest-schema-revoke",
            manifest_hash="d" * 64,
            policy_id="policy-revoke",
            public_metadata={"source_kind": "SYNTHETIC_TEST"},
        )
        receipt = self.processor.revoke_source("manifest-schema-revoke", "user_revoked")
        schema = json.loads((PHASE_ROOT / "schemas" / "RevocationReceipt.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, receipt.to_dict())

    def test_400_snapshot_rollback_removes_feedback_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = MemoryStore(root / "memory.sqlite").connect()
            snapshot = root / "before-feedback.sqlite"
            manifest = SnapshotManager.create(source, snapshot)
            FeedbackProcessor(source).commit(FeedbackProcessor(source).preview(FeedbackRecord("SUPPLEMENT", "rollback me")))
            self.assertEqual(source.stats()["feedback_receipts"], 1)
            source.close()
            restored_path = root / "restored.sqlite"
            SnapshotManager.restore(snapshot, restored_path, manifest["sha256"])
            restored = MemoryStore(restored_path).connect()
            try:
                self.assertEqual(restored.stats()["feedback_receipts"], 0)
                self.assertEqual(restored.stats()["atoms"], 0)
            finally:
                restored.close()


if __name__ == "__main__":
    unittest.main()
