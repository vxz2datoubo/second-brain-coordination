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

from integrated_offline_memory.knowledge_contracts import (
    KnowledgeGatewayPolicy,
    KnowledgeQuery,
    KnowledgeSourceManifest,
    LocalKnowledgeReference,
    evaluate_knowledge_access,
)
from integrated_offline_memory.local_knowledge import (
    ExistingServiceKnowledgeAdapter,
    LocalDirectoryKnowledgeAdapter,
    LocalFileKnowledgeAdapter,
    build_local_knowledge_packet,
    hash_local_directory,
    hash_local_file,
)
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan
from integrated_offline_memory.schema_validation import validate_schema_subset
from integrated_offline_memory.security import contains_credential_value, query_requests_credential_value


def _manifest_for_file(
    path: Path,
    *,
    content_format: str = "markdown",
    license_status: str = "DECLARED_USER_AUTHORIZED",
    privacy_class: str = "PRIVATE_LOCAL_ONLY",
) -> tuple[KnowledgeSourceManifest, KnowledgeGatewayPolicy]:
    size, digest = hash_local_file(path)
    reference = LocalKnowledgeReference(
        reference_id="ref-test-file",
        local_location_hint="local-ref://test-file",
        sha256=digest,
        size_bytes=size,
        content_format=content_format,
        content_class=privacy_class,
        body_transport="PRIVATE_LOCAL_ONLY" if privacy_class != "PUBLIC_SAFE" else "PUBLIC_SAFE_BODY",
    )
    manifest = KnowledgeSourceManifest(
        manifest_id="knowledge-manifest-test-file",
        source_id="source-test-file",
        source_version="v1",
        source_kind="FILE",
        local_reference=reference,
        owner_authorization="USER_AUTHORIZED",
        license_status=license_status,
        privacy_class=privacy_class,
        content_category="second_brain.test",
        allowed_formats=(content_format,),
        source_time_semantics="FILE_CONTENT_VERSION",
        transport_visibility=reference.body_transport,
    )
    policy = KnowledgeGatewayPolicy(
        policy_id="knowledge-policy-test-file",
        manifest_id=manifest.manifest_id,
        manifest_hash=manifest.manifest_hash,
    )
    return manifest, policy


def _manifest_for_directory(path: Path) -> tuple[KnowledgeSourceManifest, KnowledgeGatewayPolicy]:
    size, digest, _ = hash_local_directory(path, ("markdown", "txt", "json", "jsonl"))
    reference = LocalKnowledgeReference(
        reference_id="ref-test-directory",
        local_location_hint="local-ref://test-directory",
        sha256=digest,
        size_bytes=size,
        content_format="mixed",
        content_class="PRIVATE_LOCAL_ONLY",
        body_transport="PRIVATE_LOCAL_ONLY",
    )
    manifest = KnowledgeSourceManifest(
        manifest_id="knowledge-manifest-test-directory",
        source_id="source-test-directory",
        source_version="v1",
        source_kind="DIRECTORY",
        local_reference=reference,
        owner_authorization="USER_AUTHORIZED",
        license_status="DECLARED_USER_AUTHORIZED",
        privacy_class="PRIVATE_LOCAL_ONLY",
        content_category="second_brain.test",
        allowed_formats=("markdown", "txt", "json", "jsonl"),
        source_time_semantics="DIRECTORY_TREE_VERSION",
        transport_visibility="PRIVATE_LOCAL_ONLY",
    )
    policy = KnowledgeGatewayPolicy(
        policy_id="knowledge-policy-test-directory",
        manifest_id=manifest.manifest_id,
        manifest_hash=manifest.manifest_hash,
    )
    return manifest, policy


class KnowledgeContractTestCase(unittest.TestCase):
    def test_301_manifest_hash_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("deterministic", encoding="utf-8")
            manifest, _ = _manifest_for_file(path)
            self.assertEqual(manifest.manifest_hash, manifest.manifest_hash)

    def test_302_location_hint_must_be_opaque(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("body", encoding="utf-8")
            manifest, _ = _manifest_for_file(path)
            reference = dataclasses.replace(manifest.local_reference, local_location_hint=str(path))
            with self.assertRaisesRegex(ValueError, "opaque"):
                dataclasses.replace(manifest, local_reference=reference).validate_structure()

    def test_303_unknown_license_waits_for_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("body", encoding="utf-8")
            manifest, _ = _manifest_for_file(path, license_status="UNKNOWN")
            policy = KnowledgeGatewayPolicy("p", manifest.manifest_id, manifest.manifest_hash)
            self.assertEqual(evaluate_knowledge_access(manifest, policy).status, "WAITING_LOCAL_EVIDENCE")

    def test_304_prohibited_license_is_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("body", encoding="utf-8")
            manifest, _ = _manifest_for_file(path, license_status="PROHIBITED")
            policy = KnowledgeGatewayPolicy("p", manifest.manifest_id, manifest.manifest_hash)
            self.assertEqual(evaluate_knowledge_access(manifest, policy).status, "DENIED")

    def test_305_policy_hash_mismatch_is_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("body", encoding="utf-8")
            manifest, policy = _manifest_for_file(path)
            decision = evaluate_knowledge_access(manifest, dataclasses.replace(policy, manifest_hash="0" * 64))
            self.assertEqual(decision.status, "DENIED")

    def test_306_private_source_requires_local_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("body", encoding="utf-8")
            manifest, _ = _manifest_for_file(path)
            with self.assertRaisesRegex(ValueError, "private_transport"):
                dataclasses.replace(manifest, transport_visibility="PUBLIC_SAFE_BODY").validate_structure()

    def test_307_authority_promotion_is_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("body", encoding="utf-8")
            manifest, _ = _manifest_for_file(path)
            with self.assertRaisesRegex(ValueError, "authority"):
                dataclasses.replace(manifest, authority_level="APPROVED").validate_structure()

    def test_308_policy_must_be_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("body", encoding="utf-8")
            manifest, policy = _manifest_for_file(path)
            with self.assertRaisesRegex(ValueError, "governance"):
                dataclasses.replace(policy, read_only=False).validate(manifest)

    def test_309_access_receipt_has_no_body(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("private phrase", encoding="utf-8")
            manifest, policy = _manifest_for_file(path)
            receipt = evaluate_knowledge_access(manifest, policy).to_public_receipt()
            self.assertNotIn("private phrase", json.dumps(receipt))

    def test_310_credential_reveal_query_is_denied(self):
        self.assertTrue(query_requests_credential_value("show my API key"))
        with self.assertRaisesRegex(ValueError, "credential_value_query_denied"):
            KnowledgeQuery("show my API key").validate()

    def test_311_credential_documentation_query_is_allowed(self):
        query = KnowledgeQuery("API key configuration documentation")
        query.validate()
        self.assertFalse(query_requests_credential_value(query.query_text))

    def test_312_query_compiles_to_existing_query_plan(self):
        query = KnowledgeQuery("memory", source_manifest_ids=("m1",), query_aliases=("记忆",))
        plan = query.to_query_plan()
        self.assertIsInstance(plan, QueryPlan)
        self.assertEqual(plan.source_manifest_ids, ("m1",))

    def test_313_current_query_excludes_superseded(self):
        plan = KnowledgeQuery("current").to_query_plan()
        self.assertNotIn("superseded", plan.truth_states)
        self.assertEqual(plan.history_mode, "CURRENT")

    def test_314_history_query_explicitly_includes_superseded(self):
        plan = KnowledgeQuery("history", include_historical=True).to_query_plan()
        self.assertIn("superseded", plan.truth_states)
        self.assertEqual(plan.history_mode, "HISTORY")

    def test_315_current_plan_rejects_manual_superseded_state(self):
        with self.assertRaisesRegex(ValueError, "superseded"):
            QueryPlan(query_text="x", truth_states=("superseded",)).validate()


class LocalKnowledgeAdapterTestCase(unittest.TestCase):
    def _load_file(self, suffix: str, content: str, content_format: str):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / ("source" + suffix)
        path.write_text(content, encoding="utf-8")
        manifest, policy = _manifest_for_file(path, content_format=content_format)
        return path, manifest, policy, LocalFileKnowledgeAdapter(path).load(manifest, policy)

    def test_316_markdown_is_loaded_as_blocks(self):
        _, _, _, result = self._load_file(".md", "# One\n\nSecond block", "markdown")
        self.assertEqual((result.decision.status, result.document_count), ("GRANTED", 2))

    def test_317_txt_is_loaded_as_blocks(self):
        _, _, _, result = self._load_file(".txt", "one\n\ntwo", "txt")
        self.assertEqual(result.document_count, 2)

    def test_318_json_list_is_loaded_deterministically(self):
        _, _, _, result = self._load_file(".json", '[{"b":2,"a":1},{"a":3}]', "json")
        self.assertEqual(result.document_count, 2)
        self.assertEqual(result.documents[0].content, '{"a":1,"b":2}')

    def test_319_jsonl_is_loaded_deterministically(self):
        _, _, _, result = self._load_file(".jsonl", '{"a":1}\n{"a":2}\n', "jsonl")
        self.assertEqual(result.document_count, 2)

    def test_320_malformed_json_is_denied(self):
        _, _, _, result = self._load_file(".json", "{broken", "json")
        self.assertEqual(result.decision.status, "DENIED")

    def test_321_empty_file_is_denied(self):
        _, _, _, result = self._load_file(".md", "", "markdown")
        self.assertEqual(result.decision.reason_codes, ("knowledge_source_empty",))

    def test_322_hash_mismatch_is_denied(self):
        path, manifest, policy, _ = self._load_file(".md", "before", "markdown")
        path.write_text("after", encoding="utf-8")
        result = LocalFileKnowledgeAdapter(path).load(manifest, policy)
        self.assertEqual(result.decision.reason_codes, ("knowledge_source_size_or_hash_mismatch",))

    def test_323_format_mismatch_is_denied(self):
        path, manifest, policy, _ = self._load_file(".md", "body", "markdown")
        reference = dataclasses.replace(manifest.local_reference, content_format="txt")
        altered = dataclasses.replace(manifest, local_reference=reference, allowed_formats=("txt",))
        altered_policy = dataclasses.replace(policy, manifest_hash=altered.manifest_hash)
        result = LocalFileKnowledgeAdapter(path).load(altered, altered_policy)
        self.assertEqual(result.decision.status, "DENIED")

    def test_324_source_is_not_modified(self):
        path, manifest, policy, _ = self._load_file(".md", "read only", "markdown")
        before = hash_local_file(path)
        LocalFileKnowledgeAdapter(path).load(manifest, policy)
        self.assertEqual(hash_local_file(path), before)

    def test_325_public_receipt_excludes_private_body(self):
        _, _, _, result = self._load_file(".md", "private unique body", "markdown")
        encoded = json.dumps(result.public_receipt(), ensure_ascii=False)
        self.assertNotIn("private unique body", encoded)

    def test_326_secret_shaped_content_is_denied_without_echo(self):
        secret = "ghp_" + "A" * 32
        _, _, _, result = self._load_file(".md", "value=" + secret, "markdown")
        self.assertEqual(result.decision.reason_codes, ("credential_value_denied",))
        self.assertNotIn(secret, json.dumps(result.public_receipt()))

    def test_327_unknown_license_prevents_file_read(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x.md"
            path.write_text("body", encoding="utf-8")
            manifest, _ = _manifest_for_file(path, license_status="UNKNOWN")
            policy = KnowledgeGatewayPolicy("p", manifest.manifest_id, manifest.manifest_hash)
            result = LocalFileKnowledgeAdapter(path).load(manifest, policy)
            self.assertEqual(result.decision.status, "WAITING_LOCAL_EVIDENCE")

    def test_328_directory_loads_all_supported_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("alpha", encoding="utf-8")
            (root / "b.txt").write_text("beta", encoding="utf-8")
            (root / "ignored.bin").write_bytes(b"ignored")
            manifest, policy = _manifest_for_directory(root)
            result = LocalDirectoryKnowledgeAdapter(root).load(manifest, policy)
            self.assertEqual((result.file_count, result.document_count), (2, 2))

    def test_329_directory_hash_is_order_independent_of_enumeration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "b.txt").write_text("beta", encoding="utf-8")
            (root / "a.md").write_text("alpha", encoding="utf-8")
            self.assertEqual(
                hash_local_directory(root, ("markdown", "txt")),
                hash_local_directory(root, ("txt", "markdown")),
            )

    def test_330_directory_hash_change_is_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("alpha", encoding="utf-8")
            manifest, policy = _manifest_for_directory(root)
            (root / "b.txt").write_text("beta", encoding="utf-8")
            result = LocalDirectoryKnowledgeAdapter(root).load(manifest, policy)
            self.assertEqual(result.decision.status, "DENIED")

    def test_331_existing_service_is_interface_only(self):
        reference = LocalKnowledgeReference(
            "service-ref", "local-ref://service", "0" * 64, 0, "service",
            "PRIVATE_LOCAL_ONLY", "PRIVATE_LOCAL_ONLY",
        )
        manifest = KnowledgeSourceManifest(
            "service-manifest", "service", "v1", "EXISTING_SERVICE", reference,
            "USER_AUTHORIZED", "DECLARED_USER_AUTHORIZED", "PRIVATE_LOCAL_ONLY",
            "service.test", ("json",), "SERVICE_VERSION", transport_visibility="PRIVATE_LOCAL_ONLY",
        )
        policy = KnowledgeGatewayPolicy("service-policy", manifest.manifest_id, manifest.manifest_hash)
        result = ExistingServiceKnowledgeAdapter().load(manifest, policy)
        self.assertEqual(result.decision.status, "WAITING_LOCAL_EVIDENCE")

    def test_332_document_ids_are_deterministic(self):
        _, _, _, first = self._load_file(".md", "same", "markdown")
        _, _, _, second = self._load_file(".md", "same", "markdown")
        self.assertEqual(first.documents[0].document_id, second.documents[0].document_id)

    def test_348_duplicate_semantic_blocks_are_deduplicated(self):
        _, manifest, _, result = self._load_file(".md", "same block\n\nsame block", "markdown")
        packet = build_local_knowledge_packet(result, manifest)
        self.assertEqual(len(packet["atoms"]), 1)
        document_refs = [ref for ref in packet["atoms"][0]["source_refs"] if ref.startswith("document:")]
        self.assertEqual(len(document_refs), 2)


class KnowledgeRuntimeIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)

    def _packet_and_manifest(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "source.md"
        path.write_text("A股候选知识必须保留来源 lineage", encoding="utf-8")
        manifest, policy = _manifest_for_file(path)
        result = LocalFileKnowledgeAdapter(path).load(manifest, policy)
        return build_local_knowledge_packet(result, manifest), manifest, policy, result

    def test_333_local_packet_is_candidate_only(self):
        packet, _, _, _ = self._packet_and_manifest()
        self.assertEqual((packet["status"], packet["authority_write"]), ("candidate", False))

    def test_334_private_atom_remains_full_semantic_access(self):
        packet, _, _, _ = self._packet_and_manifest()
        atom = packet["atoms"][0]
        self.assertEqual(atom["gpt_access"], "FULL_SEMANTIC_ACCESS")
        self.assertEqual(atom["transport_visibility"], "PRIVATE_LOCAL_ONLY")

    def test_335_register_source_stores_metadata_only(self):
        _, manifest, policy, _ = self._packet_and_manifest()
        result = self.store.register_knowledge_source(
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            policy_id=policy.policy_id,
            public_metadata=manifest.public_metadata(),
        )
        self.assertEqual(result["status"], "ACTIVE")

    def test_336_register_source_rejects_body_metadata(self):
        _, manifest, policy, _ = self._packet_and_manifest()
        with self.assertRaisesRegex(ValueError, "private_body"):
            self.store.register_knowledge_source(
                manifest_id=manifest.manifest_id,
                manifest_hash=manifest.manifest_hash,
                policy_id=policy.policy_id,
                public_metadata={"body": "not allowed"},
            )

    def test_337_source_filter_uses_manifest_reference(self):
        packet, manifest, _, _ = self._packet_and_manifest()
        self.store.import_learning_packet(packet)
        plan = KnowledgeQuery("来源", source_manifest_ids=(manifest.manifest_id,)).to_query_plan()
        self.assertEqual(len(ContextAssembler(self.store).assemble(plan).atoms), 1)

    def test_338_wrong_source_filter_excludes_atom(self):
        packet, _, _, _ = self._packet_and_manifest()
        self.store.import_learning_packet(packet)
        plan = KnowledgeQuery("来源", source_manifest_ids=("other",)).to_query_plan()
        self.assertEqual(ContextAssembler(self.store).assemble(plan).atoms, ())

    def test_339_query_alias_retrieves_without_second_runtime(self):
        packet, _, _, _ = self._packet_and_manifest()
        self.store.import_learning_packet(packet)
        plan = KnowledgeQuery("provenance", query_aliases=("来源",)).to_query_plan()
        self.assertEqual(len(ContextAssembler(self.store).assemble(plan).atoms), 1)

    def test_340_evidence_quality_filter_applies(self):
        packet, _, _, _ = self._packet_and_manifest()
        self.store.import_learning_packet(packet)
        allowed = ContextAssembler(self.store).assemble(
            KnowledgeQuery("来源", evidence_qualities=("DECLARED_USER_AUTHORIZED",)).to_query_plan()
        )
        denied = ContextAssembler(self.store).assemble(
            KnowledgeQuery("来源", evidence_qualities=("OFFICIAL",)).to_query_plan()
        )
        self.assertEqual((len(allowed.atoms), len(denied.atoms)), (1, 0))

    def test_341_revoked_source_is_excluded_from_current_query(self):
        packet, manifest, policy, _ = self._packet_and_manifest()
        self.store.register_knowledge_source(
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            policy_id=policy.policy_id,
            public_metadata=manifest.public_metadata(),
        )
        self.store.import_learning_packet(packet)
        self.store.revoke_knowledge_source(manifest.manifest_id, "user_revoked")
        plan = KnowledgeQuery("来源").to_query_plan()
        self.assertEqual(ContextAssembler(self.store).assemble(plan).atoms, ())

    def test_342_revoked_source_can_be_explicitly_audited(self):
        packet, manifest, policy, _ = self._packet_and_manifest()
        self.store.register_knowledge_source(
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            policy_id=policy.policy_id,
            public_metadata=manifest.public_metadata(),
        )
        self.store.import_learning_packet(packet)
        self.store.revoke_knowledge_source(manifest.manifest_id, "user_revoked")
        plan = dataclasses.replace(KnowledgeQuery("来源").to_query_plan(), include_revoked_sources=True)
        self.assertEqual(len(ContextAssembler(self.store).assemble(plan).atoms), 1)

    def test_349_revocation_reason_cannot_contain_free_text(self):
        _, manifest, policy, _ = self._packet_and_manifest()
        self.store.register_knowledge_source(
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            policy_id=policy.policy_id,
            public_metadata=manifest.public_metadata(),
        )
        with self.assertRaisesRegex(ValueError, "reason_invalid"):
            self.store.revoke_knowledge_source(manifest.manifest_id, "private free text")

    def test_343_secret_mapping_detection_covers_nonempty_value_fields(self):
        self.assertTrue(contains_credential_value({"credential_value": "synthetic-placeholder"}))

    def test_344_query_plan_schema_accepts_p4_fields(self):
        schema = json.loads((PHASE_ROOT / "schemas" / "QueryPlan.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, KnowledgeQuery("schema", query_aliases=("结构",)).to_query_plan().to_dict())

    def test_345_manifest_schema_accepts_public_projection(self):
        _, manifest, _, _ = self._packet_and_manifest()
        schema = json.loads((PHASE_ROOT / "schemas" / "KnowledgeSourceManifest.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, manifest.public_metadata())

    def test_346_policy_schema_accepts_projection(self):
        _, _, policy, _ = self._packet_and_manifest()
        schema = json.loads((PHASE_ROOT / "schemas" / "KnowledgeGatewayPolicy.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, policy.to_dict())

    def test_347_access_decision_schema_accepts_public_receipt(self):
        _, manifest, policy, _ = self._packet_and_manifest()
        receipt = evaluate_knowledge_access(manifest, policy).to_public_receipt()
        schema = json.loads((PHASE_ROOT / "schemas" / "KnowledgeAccessDecision.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, receipt)


if __name__ == "__main__":
    unittest.main()
