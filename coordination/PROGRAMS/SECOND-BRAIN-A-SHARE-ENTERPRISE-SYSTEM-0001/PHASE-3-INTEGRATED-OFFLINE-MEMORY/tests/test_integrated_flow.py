from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import unittest
from datetime import date
from pathlib import Path


PHASE_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PHASE_ROOT.parent
for source_root in (
    PHASE_ROOT / "src",
    PROGRAM_ROOT / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src",
    PROGRAM_ROOT / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src",
):
    sys.path.insert(0, str(source_root))

from integrated_offline_memory.canonical import atom_id, content_hash
from integrated_offline_memory.fixtures import SyntheticDayRecord, encode_records
from integrated_offline_memory.integrated_flow import (
    context_bundle_semantic_hash,
    replay_receipt_to_learning_packet,
    run_integrated_flow,
)
from integrated_offline_memory.learning_packet import build_learning_packet
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.replay_bridge import run_p2_replay
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan
from integrated_offline_memory.schema_validation import validate_schema_subset
from integrated_offline_memory.tdx_day import TdxDayParser
from local_adapter.contracts import AdapterCapability, LocalArtifactReference, SourceManifest


def manifest(source_hash: str) -> SourceManifest:
    return SourceManifest(
        manifest_id="manifest-xt-test",
        source_id="tdx-day-xt-test",
        source_class="historical_verified",
        artifact=LocalArtifactReference(
            "artifact-xt-test", "local-only", source_hash, "PRIVATE_LOCAL_ONLY", "UNKNOWN"
        ),
        license="UNKNOWN",
        privacy_class="PRIVATE_LOCAL_ONLY",
        timezone="Asia/Shanghai",
        time_semantics="END_OF_BAR",
        available_at="2026-01-01T07:00:01Z",
        adjusted=False,
        adjustment_method="none",
        suspension_policy="unknown",
        st_policy="unknown",
        limit_rule_version="ashare-v1",
        corporate_action_policy="unknown",
        capability=AdapterCapability("day", "HISTORICAL_BAR", "confirmed", "DAILY_AGGREGATE_BAR"),
        synthetic=False,
        field_semantics_version="tdx-day-partial-v1",
    )


def replay_receipt():
    records = [
        SyntheticDayRecord(
            date_raw=20260105 + index,
            open_raw=1000 + index * 10,
            high_raw=1120 + index * 10,
            low_raw=900 + index * 10,
            close_raw=1050 + index * 10,
            volume_raw=10000 + index * 100,
        )
        for index in range(8)
    ]
    payload = encode_records(*records)
    source_hash = hashlib.sha256(payload).hexdigest()
    parsed = TdxDayParser().parse_bytes(
        payload,
        manifest_id="manifest-xt-test",
        policy_id="policy-xt-test",
        artifact_sha256=source_hash,
        requested_as_of_date=date(2026, 12, 31),
    )
    return run_p2_replay(
        parsed,
        manifest(source_hash),
        symbol="300418",
        exchange="SZ",
        requested_as_of="2026-12-31T00:00:00Z",
    )


class IntegratedFlowAcceptanceTestCase(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)

    def test_xt_001_hash_stability(self):
        receipt = replay_receipt()
        first = replay_receipt_to_learning_packet(receipt)
        second = replay_receipt_to_learning_packet(receipt)
        self.assertEqual(first["packet_content_hash"], second["packet_content_hash"])
        self.assertEqual(first["packet_id"], second["packet_id"])

    def test_xt_002_packet_roundtrip_and_idempotency(self):
        packet = replay_receipt_to_learning_packet(replay_receipt())
        roundtrip = json.loads(json.dumps(packet, ensure_ascii=False, sort_keys=True))
        first = self.store.import_learning_packet(roundtrip)
        second = self.store.import_learning_packet(roundtrip)
        self.assertEqual(first["status"], "IMPORTED")
        self.assertEqual(second["status"], "IDEMPOTENT_DUPLICATE")

    def test_xt_003_conflict_propagation(self):
        left = atom_id("candidate field interpretation A", "observation", "a_share.field_semantics")
        right = atom_id("candidate field interpretation B", "observation", "a_share.field_semantics")
        packet = build_learning_packet(
            source_manifest_ids=["manifest-xt-test"],
            source_hash="a" * 64,
            validation_report={"status": "SYNTHETIC_TEST", "research_only": True},
            evidence_refs=["evidence:xt-003"],
            atoms=[
                {"id": left, "statement": "candidate field interpretation A", "atom_type": "observation", "scope": "a_share.field_semantics", "knowledge_status": "conflict"},
                {"id": right, "statement": "candidate field interpretation B", "atom_type": "observation", "scope": "a_share.field_semantics", "knowledge_status": "conflict"},
            ],
            conflicts=[{"id": "conf-xt-003", "atom_id_a": left, "atom_id_b": right, "conflict_type": "SEMANTIC"}],
        )
        self.store.import_learning_packet(packet)
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="field interpretation", include_conflicts=True))
        self.assertEqual([item["id"] for item in bundle.conflicts], ["conf-xt-003"])

    def test_xt_004_unknown_preservation(self):
        flow, packet, bundle = run_integrated_flow(replay_receipt(), self.store)
        self.assertEqual(len(packet["unknowns"]), len(replay_receipt().unknowns))
        self.assertEqual(set(flow.unknown_ids), {item["id"] for item in bundle.unknowns})
        self.assertTrue(any(item["question"] == "volume_unit_unknown" for item in bundle.unknowns))

    def test_xt_005_credential_value_isolation(self):
        packet = replay_receipt_to_learning_packet(replay_receipt())
        packet["credential_value"] = "synthetic-nonsecret-test-value"
        with self.assertRaisesRegex(ValueError, "credential_value_denied"):
            self.store.import_learning_packet(packet)
        self.assertEqual(self.store.stats()["packets"], 0)

    def test_xt_006_512_atom_scale(self):
        atoms = [
            {"statement": f"synthetic integrated atom {index} scale evidence", "atom_type": "observation", "scope": "scale"}
            for index in range(512)
        ]
        packet = build_learning_packet(
            source_manifest_ids=["manifest-scale"],
            source_hash="c" * 64,
            validation_report={"status": "SYNTHETIC_SCALE", "research_only": True},
            evidence_refs=["evidence:xt-006"],
            atoms=atoms,
        )
        self.store.import_learning_packet(packet)
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="scale evidence", budget=512))
        self.assertEqual(len(bundle.atoms), 512)
        self.assertTrue(self.store.integrity_check()["integrity_ok"])

    def test_end_to_end_receipt_is_candidate_only(self):
        flow, packet, bundle = run_integrated_flow(replay_receipt(), self.store)
        self.assertTrue(flow.research_only)
        self.assertTrue(flow.no_trade_gate)
        self.assertFalse(flow.authority_write)
        self.assertFalse(flow.raw_records_exported)
        self.assertEqual(packet["status"], "candidate")
        self.assertEqual(bundle.semantic_access_state, "FULL_SEMANTIC_ACCESS_CANDIDATE_ONLY")

    def test_end_to_end_source_lineage_is_complete(self):
        flow, packet, bundle = run_integrated_flow(replay_receipt(), self.store)
        self.assertIn("manifest:manifest-xt-test", flow.source_lineage)
        self.assertTrue(any(item.startswith("artifact-sha256:") for item in flow.source_lineage))
        self.assertEqual(flow.packet_content_hash, content_hash({key: value for key, value in packet.items() if key not in {"packet_content_hash", "idempotency_key"}}))
        self.assertEqual(flow.context_bundle_hash, context_bundle_semantic_hash(bundle))

    def test_context_semantic_hash_is_stable_across_stores(self):
        receipt = replay_receipt()
        first_flow, _, _ = run_integrated_flow(receipt, self.store)
        second_store = MemoryStore().connect()
        self.addCleanup(second_store.close)
        second_flow, _, _ = run_integrated_flow(receipt, second_store)
        self.assertEqual(first_flow.context_bundle_hash, second_flow.context_bundle_hash)

    def test_replay_boundary_rejects_authority_write(self):
        receipt = dataclasses.replace(replay_receipt(), authority_write=True)
        with self.assertRaisesRegex(ValueError, "authority_write"):
            replay_receipt_to_learning_packet(receipt)

    def test_replay_boundary_rejects_raw_export(self):
        receipt = dataclasses.replace(replay_receipt(), raw_records_exported=True)
        with self.assertRaisesRegex(ValueError, "raw_record_export"):
            replay_receipt_to_learning_packet(receipt)

    def test_integrated_flow_receipt_schema_validates(self):
        flow, _, _ = run_integrated_flow(replay_receipt(), self.store)
        schema = json.loads((PHASE_ROOT / "schemas" / "IntegratedFlowReceipt.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, flow.public_payload())


if __name__ == "__main__":
    unittest.main()
