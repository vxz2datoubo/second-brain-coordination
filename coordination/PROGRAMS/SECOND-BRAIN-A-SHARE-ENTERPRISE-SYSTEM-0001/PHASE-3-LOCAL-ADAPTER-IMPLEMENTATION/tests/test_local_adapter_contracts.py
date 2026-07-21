"""Synthetic-only contract tests. No network, service, broker, or real-data access."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from local_adapter import (  # noqa: E402
    AdapterCapability, AdapterStatus, CredentialReference, InMemoryCapabilityProbe,
    InMemoryKnowledgeGateway, InMemoryLearningPacketAdapter, LocalArtifactReference,
    ManifestValidator, SourceManifest, SyntheticOfflineDatasetAdapter, canonical_hash,
    deserialize_contract, serialize_contract,
)


AS_OF = "2026-01-31T23:59:59Z"


def make_artifact(path: Path) -> LocalArtifactReference:
    text = path.read_text(encoding="utf-8")
    return LocalArtifactReference("artifact.synthetic.001", "synthetic-fixture", hashlib.sha256(text.encode()).hexdigest())


def make_manifest(path: Path, **changes: object) -> SourceManifest:
    base = SourceManifest(
        manifest_id="manifest.synthetic.001", source_id="synthetic.public.safe",
        source_class="synthetic", artifact=make_artifact(path), license="CC0-1.0",
        privacy_class="PUBLIC_SAFE", timezone="UTC", time_semantics="END_OF_BAR",
        available_at="2026-01-30T16:00:00Z", adjusted=False, adjustment_method="none",
        suspension_policy="explicit_boolean", st_policy="explicit_boolean", limit_rule_version="ashare-v1",
        corporate_action_policy="none", capability=AdapterCapability("cap.synthetic.bar", "HISTORICAL_BAR", "confirmed", "BAR"),
    )
    return replace(base, **changes)


class LocalAdapterContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "bars.json"
        self.path.write_text(json.dumps({"records": [{"symbol": "000001.SZ", "close": 10.5, "event_time": "2026-01-30T15:00:00Z"}]}), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_manifest_verified(self) -> None:
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path), AS_OF).status, AdapterStatus.VERIFIED)

    def test_manifest_core_hash_is_deterministic(self) -> None:
        self.assertEqual(canonical_hash({"b": 1, "a": 2}), canonical_hash({"a": 2, "b": 1}))

    def test_synthetic_json_loads(self) -> None:
        result = SyntheticOfflineDatasetAdapter(self.path).load(make_manifest(self.path), AS_OF)
        self.assertEqual((result.status, result.payload["record_count"]), (AdapterStatus.VERIFIED, 1))

    def test_synthetic_hash_repeatable(self) -> None:
        adapter = SyntheticOfflineDatasetAdapter(self.path)
        left, right = adapter.load(make_manifest(self.path), AS_OF), adapter.load(make_manifest(self.path), AS_OF)
        self.assertEqual(left.payload["core_hash"], right.payload["core_hash"])

    def test_csv_loads(self) -> None:
        path = Path(self.tmp.name) / "bars.csv"
        path.write_text("symbol,close\n000001.SZ,10.5\n", encoding="utf-8")
        self.assertEqual(SyntheticOfflineDatasetAdapter(path).load(make_manifest(path), AS_OF).status, AdapterStatus.VERIFIED)

    def test_jsonl_loads(self) -> None:
        path = Path(self.tmp.name) / "bars.jsonl"
        path.write_text('{"symbol":"000001.SZ","close":10.5}\n', encoding="utf-8")
        self.assertEqual(SyntheticOfflineDatasetAdapter(path).load(make_manifest(path), AS_OF).status, AdapterStatus.VERIFIED)

    def test_real_source_is_blocked(self) -> None:
        manifest = make_manifest(self.path, synthetic=False, source_class="historical_verified")
        self.assertEqual(ManifestValidator().validate(manifest, AS_OF).status, AdapterStatus.BLOCKED_BY_POLICY)

    def test_hash_mismatch_is_rejected(self) -> None:
        manifest = make_manifest(self.path, artifact=replace(make_artifact(self.path), sha256="0" * 64))
        self.assertEqual(SyntheticOfflineDatasetAdapter(self.path).load(manifest, AS_OF).status, AdapterStatus.REJECTED)

    def test_missing_fixture_is_rejected(self) -> None:
        missing = Path(self.tmp.name) / "missing.json"
        manifest = make_manifest(self.path, artifact=LocalArtifactReference("artifact.synthetic.001", "synthetic-fixture", "0" * 64))
        self.assertEqual(SyntheticOfflineDatasetAdapter(missing).load(manifest, AS_OF).status, AdapterStatus.REJECTED)

    def test_unknown_time_is_payload_only(self) -> None:
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, time_semantics="UNKNOWN"), AS_OF).status, AdapterStatus.PAYLOAD_SAMPLE_ONLY)

    def test_future_availability_is_rejected(self) -> None:
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, available_at="2026-02-01T00:00:00Z"), AS_OF).status, AdapterStatus.REJECTED)

    def test_unknown_license_is_legacy_unknown(self) -> None:
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, license=""), AS_OF).status, AdapterStatus.LEGACY_UNKNOWN)

    def test_bad_timezone_is_rejected(self) -> None:
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, timezone="Mars/Olympus"), AS_OF).status, AdapterStatus.REJECTED)

    def test_adjusted_without_method_is_rejected(self) -> None:
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, adjusted=True, adjustment_method="none"), AS_OF).status, AdapterStatus.REJECTED)

    def test_missing_ashare_policy_is_partial(self) -> None:
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, st_policy="UNKNOWN"), AS_OF).status, AdapterStatus.PARTIALLY_VERIFIED)

    def test_unknown_entitlement_is_partial(self) -> None:
        capability = AdapterCapability("cap.synthetic.bar", "HISTORICAL_BAR", "unknown", "BAR")
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, capability=capability), AS_OF).status, AdapterStatus.PARTIALLY_VERIFIED)

    def test_invalid_l2_semantic_is_rejected(self) -> None:
        capability = AdapterCapability("cap.l2", "L2_AGGREGATE", "confirmed", "RAW_TRADE_TICK")
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, capability=capability), AS_OF).status, AdapterStatus.REJECTED)

    def test_l2_aggregate_vendor_semantic_is_allowed(self) -> None:
        capability = AdapterCapability("cap.l2", "L2_AGGREGATE", "confirmed", "VENDOR_DEFINED_AGGREGATE")
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, capability=capability), AS_OF).status, AdapterStatus.VERIFIED)

    def test_invalid_artifact_class_is_rejected(self) -> None:
        bad = replace(make_artifact(self.path), content_class="PRIVATE_RAW")
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, artifact=bad), AS_OF).status, AdapterStatus.REJECTED)

    def test_bad_source_class_does_not_bypass_synthetic_flag(self) -> None:
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, source_class="legacy_unknown", synthetic=False), AS_OF).status, AdapterStatus.BLOCKED_BY_POLICY)

    def test_knowledge_returns_candidate_atoms(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "a", "content": "A share T plus one", "status": "candidate"}])
        result = gateway.query("share", 50)
        self.assertEqual((result.status, result.payload["atoms"][0]["atom_id"]), (AdapterStatus.VERIFIED, "a"))

    def test_knowledge_budget_omits_atom(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "a", "content": "momentum " * 20, "status": "candidate"}])
        self.assertIn("a", gateway.query("momentum", 1).payload["omitted_due_to_context_budget"])

    def test_knowledge_allows_credential_documentation_query(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "doc", "content": "API Key 文档和 Token 轮换原则", "status": "approved"}])
        self.assertEqual(gateway.query("API Key", 50).status, AdapterStatus.VERIFIED)

    def test_knowledge_excludes_rejected_atom(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "a", "content": "market", "status": "rejected"}])
        self.assertEqual(gateway.query("market", 20).payload["atoms"], [])

    def test_knowledge_requires_positive_budget(self) -> None:
        self.assertEqual(InMemoryKnowledgeGateway([]).query("market", 0).status, AdapterStatus.REJECTED)

    def test_candidate_packet_is_accepted_without_promotion(self) -> None:
        packet = {"packet_id": "p", "packet_content_hash": "h", "idempotency_key": "i", "base_knowledge_revision": "r", "status": "candidate", "authority_write": False}
        result = InMemoryLearningPacketAdapter().emit(packet)
        self.assertTrue(result.payload["candidate_only"])

    def test_approved_packet_is_rejected(self) -> None:
        packet = {"packet_id": "p", "packet_content_hash": "h", "idempotency_key": "i", "base_knowledge_revision": "r", "status": "approved"}
        self.assertEqual(InMemoryLearningPacketAdapter().emit(packet).status, AdapterStatus.REJECTED)

    def test_authority_write_packet_is_rejected(self) -> None:
        packet = {"packet_id": "p", "packet_content_hash": "h", "idempotency_key": "i", "base_knowledge_revision": "r", "status": "candidate", "authority_write": True}
        self.assertEqual(InMemoryLearningPacketAdapter().emit(packet).status, AdapterStatus.REJECTED)

    def test_incomplete_packet_is_rejected(self) -> None:
        self.assertEqual(InMemoryLearningPacketAdapter().emit({"status": "candidate"}).status, AdapterStatus.REJECTED)

    def test_packet_credential_documentation_is_allowed(self) -> None:
        packet = {"packet_id": "p", "packet_content_hash": "h", "idempotency_key": "i", "base_knowledge_revision": "r", "status": "candidate", "note": "Token轮换和API Key文档"}
        self.assertEqual(InMemoryLearningPacketAdapter().emit(packet).status, AdapterStatus.VERIFIED)

    def test_credential_reference_is_metadata_only(self) -> None:
        ref = CredentialReference("cred.tdx", "local adapter test", "synthetic", "2026-01-01T00:00:00Z", "a" * 16, "local reference")
        ref.validate()

    def test_credential_reference_allows_category_terminology(self) -> None:
        ref = CredentialReference("cred.tdx", "private key rotation documentation", "synthetic", "2026-01-01T00:00:00Z", "a" * 16, "local reference")
        ref.validate()

    def test_capability_probe_is_synthetic(self) -> None:
        capability = AdapterCapability("cap.synthetic.bar", "HISTORICAL_BAR", "confirmed", "BAR")
        self.assertEqual(InMemoryCapabilityProbe().probe(capability).payload["probe"], "synthetic_in_memory_only")

    def test_capability_probe_unknown_entitlement_is_partial(self) -> None:
        capability = AdapterCapability("cap.synthetic.bar", "HISTORICAL_BAR", "unknown", "BAR")
        self.assertEqual(InMemoryCapabilityProbe().probe(capability).status, AdapterStatus.PARTIALLY_VERIFIED)

    def test_adapter_result_is_never_authority_write(self) -> None:
        self.assertFalse(ManifestValidator().validate(make_manifest(self.path), AS_OF).authority_write)

    def test_adapter_result_always_has_no_trade_gate(self) -> None:
        self.assertTrue(ManifestValidator().validate(make_manifest(self.path), AS_OF).no_trade_gate)

    def test_json_root_array_loads(self) -> None:
        path = Path(self.tmp.name) / "array.json"
        path.write_text('[{"symbol":"000001.SZ"}]', encoding="utf-8")
        self.assertEqual(SyntheticOfflineDatasetAdapter(path).load(make_manifest(path), AS_OF).payload["record_count"], 1)

    def test_unsupported_extension_is_rejected(self) -> None:
        path = Path(self.tmp.name) / "bars.txt"
        path.write_text("x", encoding="utf-8")
        self.assertEqual(SyntheticOfflineDatasetAdapter(path).load(make_manifest(path), AS_OF).status, AdapterStatus.REJECTED)

    def test_chinese_company_name_retrieval(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "kunlun", "content": "昆仑万维发布世界模型", "status": "approved"}])
        self.assertEqual(gateway.query("昆仑万维", 50).payload["atoms"][0]["atom_id"], "kunlun")

    def test_chinese_professional_term_retrieval(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "term", "content": "筹码分布和换手率必须结合T+1理解", "status": "candidate"}])
        self.assertEqual(gateway.query("筹码分布", 50).status, AdapterStatus.VERIFIED)

    def test_mixed_language_retrieval(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "mixed", "content": "A股 T+1 VWAP 风险控制", "status": "approved"}])
        self.assertEqual(gateway.query("A股 VWAP", 50).payload["atoms"][0]["atom_id"], "mixed")

    def test_unicode_normalization_retrieval(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "normalized", "content": "Ａ股市场结构", "status": "approved"}])
        self.assertEqual(gateway.query("A股", 50).status, AdapterStatus.VERIFIED)

    def test_conflict_atom_remains_retrievable(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "conflict", "content": "策略证据存在冲突", "status": "conflict"}])
        self.assertEqual(gateway.query("策略证据", 50).payload["atoms"][0]["status"], "conflict")

    def test_superseded_atom_remains_retrievable(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "old", "content": "旧版复权规则", "status": "superseded"}])
        self.assertEqual(gateway.query("复权规则", 50).payload["atoms"][0]["status"], "superseded")

    def test_unknown_atom_remains_retrievable(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "unknown", "content": "未知字段语义仍待验证", "status": "unknown"}])
        self.assertEqual(gateway.query("字段语义", 50).payload["atoms"][0]["status"], "unknown")

    def test_rejected_atom_is_not_retrievable(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "bad", "content": "错误历史结论", "status": "rejected"}])
        self.assertEqual(gateway.query("历史结论", 50).payload["atoms"], [])

    def test_real_secret_pattern_in_packet_is_blocked(self) -> None:
        packet = {"packet_id": "p", "packet_content_hash": "h", "idempotency_key": "i", "base_knowledge_revision": "r", "status": "candidate", "credential_value": "ghp_abcdefghijklmnopqrstuvwxyz123456"}
        self.assertEqual(InMemoryLearningPacketAdapter().emit(packet).status, AdapterStatus.BLOCKED_BY_POLICY)

    def test_explicit_credential_value_field_is_blocked_even_placeholder(self) -> None:
        packet = {"packet_id": "p", "packet_content_hash": "h", "idempotency_key": "i", "base_knowledge_revision": "r", "status": "candidate", "credential_value": "<LOCAL_ONLY>"}
        self.assertEqual(InMemoryLearningPacketAdapter().emit(packet).status, AdapterStatus.BLOCKED_BY_POLICY)

    def test_invalid_placeholder_in_document_is_allowed(self) -> None:
        gateway = InMemoryKnowledgeGateway([{"atom_id": "placeholder", "content": "示例 api_key=YOUR_KEY 仅用于文档", "status": "approved"}])
        self.assertEqual(gateway.query("api_key", 50).status, AdapterStatus.VERIFIED)

    def test_private_local_artifact_is_valid_contract_metadata(self) -> None:
        artifact = replace(make_artifact(self.path), content_class="PRIVATE_LOCAL_ONLY", license_status="LICENSED")
        artifact.validate()

    def test_licensed_local_real_source_is_blocked_not_rejected(self) -> None:
        artifact = replace(make_artifact(self.path), content_class="LICENSED_LOCAL", license_status="LICENSED")
        manifest = make_manifest(self.path, artifact=artifact, synthetic=False, source_class="historical_verified")
        self.assertEqual(ManifestValidator().validate(manifest, AS_OF).status, AdapterStatus.BLOCKED_BY_POLICY)

    def test_invalid_content_class_is_rejected(self) -> None:
        artifact = replace(make_artifact(self.path), content_class="MYSTERY")
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, artifact=artifact), AS_OF).status, AdapterStatus.REJECTED)

    def test_unknown_license_is_not_verified(self) -> None:
        manifest = make_manifest(self.path, license="UNKNOWN")
        self.assertEqual(ManifestValidator().validate(manifest, AS_OF).status, AdapterStatus.LEGACY_UNKNOWN)

    def test_undeclared_artifact_license_is_not_verified(self) -> None:
        artifact = replace(make_artifact(self.path), license_status="UNDECLARED")
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, artifact=artifact), AS_OF).status, AdapterStatus.LEGACY_UNKNOWN)

    def test_license_conflict_is_partial(self) -> None:
        artifact = replace(make_artifact(self.path), license_status="CONFLICT")
        self.assertEqual(ManifestValidator().validate(make_manifest(self.path, artifact=artifact), AS_OF).status, AdapterStatus.PARTIALLY_VERIFIED)

    def test_manifest_serialization_round_trip(self) -> None:
        manifest = make_manifest(self.path)
        restored = deserialize_contract("SourceManifest", serialize_contract(manifest))
        self.assertEqual(restored, manifest)

    def test_capability_serialization_round_trip(self) -> None:
        capability = AdapterCapability("cap", "HISTORICAL_BAR", "confirmed", "BAR")
        self.assertEqual(deserialize_contract("AdapterCapability", serialize_contract(capability)), capability)

    def test_result_serialization_round_trip(self) -> None:
        result = ManifestValidator().validate(make_manifest(self.path), AS_OF)
        self.assertEqual(deserialize_contract("AdapterResult", serialize_contract(result)), result)

    def test_unknown_contract_field_is_rejected(self) -> None:
        payload = serialize_contract(AdapterCapability("cap", "HISTORICAL_BAR", "confirmed", "BAR"))
        payload["unexpected"] = True
        with self.assertRaises(ValueError):
            deserialize_contract("AdapterCapability", payload)

    def test_incompatible_contract_version_is_rejected(self) -> None:
        payload = serialize_contract(AdapterCapability("cap", "HISTORICAL_BAR", "confirmed", "BAR"))
        payload["schema_version"] = "2.0.0"
        with self.assertRaises(ValueError):
            deserialize_contract("AdapterCapability", payload)

    def test_machine_readable_schema_files_parse(self) -> None:
        schema_dir = ROOT / "schemas"
        expected = {"LocalArtifactReference", "CredentialReference", "AdapterCapability", "AdapterResult", "SourceManifest"}
        parsed = {path.name.removesuffix(".schema.json"): json.loads(path.read_text(encoding="utf-8")) for path in schema_dir.glob("*.schema.json")}
        self.assertEqual(set(parsed), expected)
        self.assertTrue(all(item["additionalProperties"] is False for item in parsed.values()))


if __name__ == "__main__":
    unittest.main()
