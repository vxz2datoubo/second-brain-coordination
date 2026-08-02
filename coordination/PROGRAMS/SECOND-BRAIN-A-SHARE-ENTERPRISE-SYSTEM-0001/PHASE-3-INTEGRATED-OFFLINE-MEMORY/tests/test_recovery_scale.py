from __future__ import annotations

import dataclasses
import contextlib
import io
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
from integrated_offline_memory.gateway_cli import main as gateway_cli_main
from integrated_offline_memory.learning_packet import build_learning_packet
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.recovery import export_rebuild_bundle, rebuild_memory_store
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan
from integrated_offline_memory.schema_validation import validate_schema_subset
from integrated_offline_memory.security import CredentialValueDenied
from integrated_offline_memory.snapshot import SnapshotManager


def packet(atoms, *, source_hash="1" * 64, unknowns=None, manifest_id="manifest-rebuild"):
    return build_learning_packet(
        source_manifest_ids=[manifest_id],
        source_hash=source_hash,
        validation_report={"status": "SYNTHETIC_SCALE", "research_only": True},
        evidence_refs=["manifest:" + manifest_id, "evidence:synthetic-scale"],
        atoms=atoms,
        unknowns=unknowns or [],
    )


class RecoveryScaleTestCase(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)

    def test_401_2000_atom_scale_is_integrity_clean(self):
        atoms = [{
            "atom_type": "fact",
            "statement": f"public safe scale atom {index} cluster-{index % 20}",
            "scope": "scale-2000",
            "confidence": 0.7,
        } for index in range(2000)]
        self.store.import_learning_packet(packet(atoms))
        self.assertEqual(self.store.stats()["atoms"], 2000)
        self.assertTrue(self.store.integrity_check()["integrity_ok"])

    def test_402_2000_atom_query_is_budget_bounded(self):
        atoms = [{
            "atom_type": "fact",
            "statement": f"bounded retrieval item {index}",
            "scope": "scale-query",
        } for index in range(2000)]
        self.store.import_learning_packet(packet(atoms, source_hash="2" * 64))
        result = ContextAssembler(self.store).assemble(QueryPlan(query_text="bounded retrieval", budget=25))
        self.assertEqual(len(result.atoms), 25)
        self.assertEqual(len(result.omitted_due_to_budget), 1975)

    def test_403_rebuild_bundle_is_deterministic(self):
        self.store.import_learning_packet(packet([{"atom_type": "fact", "statement": "rebuild deterministic"}]))
        self.assertEqual(export_rebuild_bundle(self.store).bundle_hash, export_rebuild_bundle(self.store).bundle_hash)

    def test_404_two_empty_store_rebuilds_match(self):
        atoms = [{"atom_type": "fact", "statement": f"rebuild atom {index}"} for index in range(100)]
        self.store.import_learning_packet(packet(atoms, source_hash="3" * 64))
        bundle = export_rebuild_bundle(self.store)
        first, first_receipt = rebuild_memory_store(bundle)
        second, second_receipt = rebuild_memory_store(bundle)
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        self.assertEqual(first_receipt.semantic_state_hash, second_receipt.semantic_state_hash)
        self.assertEqual(first_receipt.semantic_state_hash, self.store.semantic_state_hash())

    def test_405_rebuild_preserves_resolved_unknown(self):
        value = packet([{"atom_type": "fact", "statement": "unknown context"}])
        atom_id = value["atoms"][0]["id"]
        value = packet(
            [{"id": atom_id, "atom_type": "fact", "statement": "unknown context"}],
            unknowns=[{"id": "unknown-rebuild", "question": "resolved?", "related_atom_ids": [atom_id]}],
            source_hash="4" * 64,
        )
        self.store.import_learning_packet(value)
        self.store.resolve_unknown("unknown-rebuild", atom_id)
        rebuilt, _ = rebuild_memory_store(export_rebuild_bundle(self.store))
        self.addCleanup(rebuilt.close)
        self.assertEqual(rebuilt.get_unknown("unknown-rebuild")["status"], "RESOLVED")

    def test_406_rebuild_preserves_revoked_source_state(self):
        manifest_id = "manifest-rebuild-revoked"
        self.store.register_knowledge_source(
            manifest_id=manifest_id,
            manifest_hash="5" * 64,
            policy_id="policy-rebuild",
            public_metadata={"source_kind": "SYNTHETIC_TEST"},
        )
        self.store.import_learning_packet(packet(
            [{"atom_type": "fact", "statement": "revoked rebuild source"}],
            source_hash="5" * 64,
            manifest_id=manifest_id,
        ))
        self.store.revoke_knowledge_source(manifest_id, "user_revoked")
        rebuilt, receipt = rebuild_memory_store(export_rebuild_bundle(self.store))
        self.addCleanup(rebuilt.close)
        self.assertEqual(rebuilt.source_status(manifest_id), "REVOKED")
        self.assertEqual(receipt.semantic_state_hash, self.store.semantic_state_hash())

    def test_407_rebuild_preserves_feedback_receipt(self):
        processor = FeedbackProcessor(self.store)
        feedback = processor.commit(processor.preview(FeedbackRecord("SUPPLEMENT", "rebuild feedback")))
        rebuilt, receipt = rebuild_memory_store(export_rebuild_bundle(self.store))
        self.addCleanup(rebuilt.close)
        self.assertEqual(rebuilt.get_feedback_receipt(feedback.feedback_id)["packet_id"], feedback.packet_id)
        self.assertEqual(receipt.semantic_state_hash, self.store.semantic_state_hash())

    def test_408_tampered_rebuild_bundle_is_rejected(self):
        self.store.import_learning_packet(packet([{"atom_type": "fact", "statement": "tamper bundle"}]))
        bundle = export_rebuild_bundle(self.store)
        with self.assertRaisesRegex(ValueError, "bundle_hash_mismatch"):
            rebuild_memory_store(dataclasses.replace(bundle, bundle_hash="0" * 64))

    def test_409_unsupported_rebuild_schema_is_rejected(self):
        bundle = export_rebuild_bundle(self.store)
        with self.assertRaisesRegex(ValueError, "schema_unsupported"):
            rebuild_memory_store(dataclasses.replace(bundle, schema_version="2.0.0"))

    def test_410_governance_boundary_is_enforced(self):
        bundle = export_rebuild_bundle(self.store)
        with self.assertRaisesRegex(ValueError, "governance_boundary"):
            rebuild_memory_store(dataclasses.replace(bundle, authority_write=True))

    def test_411_credential_value_in_rebuild_is_denied(self):
        bundle = export_rebuild_bundle(self.store)
        bad_source = ({
            "manifest_id": "secret-source",
            "manifest_hash": "6" * 64,
            "policy_id": "p",
            "status": "ACTIVE",
            "public_metadata": {"credential_value": "synthetic-placeholder"},
        },)
        modified = dataclasses.replace(bundle, knowledge_sources=bad_source)
        payload = modified.to_dict()
        payload.pop("bundle_hash")
        from integrated_offline_memory.canonical import content_hash
        modified = dataclasses.replace(modified, bundle_hash=content_hash(payload))
        with self.assertRaises(CredentialValueDenied):
            rebuild_memory_store(modified)

    def test_412_snapshot_restore_keeps_semantic_state_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = MemoryStore(root / "source.sqlite").connect()
            source.import_learning_packet(packet([{"atom_type": "fact", "statement": "snapshot semantic"}]))
            expected = source.semantic_state_hash()
            snapshot = root / "snapshot.sqlite"
            manifest = SnapshotManager.create(source, snapshot)
            source.close()
            restored_path = root / "restored.sqlite"
            SnapshotManager.restore(snapshot, restored_path, manifest["sha256"])
            restored = MemoryStore(restored_path).connect()
            try:
                self.assertEqual(restored.semantic_state_hash(), expected)
            finally:
                restored.close()

    def test_413_cli_invalid_json_returns_nonzero_with_repair_hint(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("{broken", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = gateway_cli_main(["validate-packet", "--input", str(path)])
            result = json.loads(stderr.getvalue())
            self.assertNotEqual(code, 0)
            self.assertEqual(result["repair_hint"], "provide_a_readable_utf8_json_learning_packet")

    def test_414_cli_valid_packet_returns_public_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "packet.json"
            value = packet([{"atom_type": "fact", "statement": "cli valid packet"}])
            path.write_text(json.dumps(value), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = gateway_cli_main(["validate-packet", "--input", str(path)])
            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual((result["authority_write"], result["no_trade_gate"]), (False, True))

    def test_415_rebuild_bundle_schema_validates(self):
        bundle = export_rebuild_bundle(self.store)
        schema = json.loads((PHASE_ROOT / "schemas" / "MemoryRebuildBundle.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, bundle.to_dict())

    def test_416_rebuild_receipt_schema_validates(self):
        rebuilt, receipt = rebuild_memory_store(export_rebuild_bundle(self.store))
        self.addCleanup(rebuilt.close)
        schema = json.loads((PHASE_ROOT / "schemas" / "RebuildReceipt.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, receipt.to_dict())


if __name__ == "__main__":
    unittest.main()
