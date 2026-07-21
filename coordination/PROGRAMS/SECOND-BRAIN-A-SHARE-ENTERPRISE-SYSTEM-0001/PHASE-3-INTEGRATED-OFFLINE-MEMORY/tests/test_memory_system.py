from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import tempfile
import time
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

from integrated_offline_memory.canonical import atom_id, content_hash, normalize_text, relation_id
from integrated_offline_memory.evaluation import populate_retrieval_fixture, run_retrieval_regression
from integrated_offline_memory.fusion import FusionEngine
from integrated_offline_memory.learning_packet import build_learning_packet, verify_learning_packet
from integrated_offline_memory.memory_store import MemoryStore, tokenize
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan
from integrated_offline_memory.schema_validation import validate_schema_subset
from integrated_offline_memory.snapshot import SnapshotManager


def atom(statement: str, *, atom_type: str = "fact", scope: str = "test", confidence: float = 0.8, **extra):
    result = {"atom_type": atom_type, "statement": statement, "scope": scope, "confidence": confidence}
    result.update(extra)
    return result


def packet(atoms, *, relations=None, unknowns=None, conflicts=None, source_hash="b" * 64):
    return build_learning_packet(
        source_manifest_ids=["manifest-test"],
        source_hash=source_hash,
        validation_report={"status": "SYNTHETIC_TEST", "research_only": True},
        evidence_refs=["evidence-test"],
        atoms=atoms,
        relations=relations or [],
        unknowns=unknowns or [],
        conflicts=conflicts or [],
    )


class MemorySystemTestCase(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)

    def test_201_nfkc_normalizes_full_width(self):
        self.assertEqual(normalize_text("ＶＷＡＰ　研究"), "VWAP 研究")

    def test_202_whitespace_is_collapsed(self):
        self.assertEqual(normalize_text("a\n  b"), "a b")

    def test_203_content_hash_ignores_dict_order(self):
        self.assertEqual(content_hash({"a": 1, "b": 2}), content_hash({"b": 2, "a": 1}))

    def test_204_atom_id_is_deterministic(self):
        self.assertEqual(atom_id("A", "fact"), atom_id("A", "fact"))

    def test_205_relation_id_is_deterministic(self):
        self.assertEqual(relation_id("a", "b", "supports"), relation_id("a", "b", "supports"))

    def test_206_packet_is_deterministic(self):
        self.assertEqual(packet([atom("A")]), packet([atom("A")]))

    def test_207_packet_is_candidate_only(self):
        value = packet([atom("A")])
        self.assertEqual((value["status"], value["authority_write"]), ("candidate", False))

    def test_208_packet_has_manifest_and_validation(self):
        value = packet([atom("A")])
        self.assertEqual(value["source_manifest_ids"], ["manifest-test"])
        self.assertIn("validation_report", value)

    def test_209_packet_verification_rejects_authority(self):
        value = packet([atom("A")])
        value["authority_write"] = True
        self.assertFalse(verify_learning_packet(value)["valid"])

    def test_210_packet_verification_rejects_missing_relation_endpoint(self):
        value = packet([atom("A")])
        value["relations"] = [{"source_atom_id": value["atoms"][0]["id"], "target_atom_id": "missing"}]
        self.assertFalse(verify_learning_packet(value)["valid"])

    def test_211_insert_atom_auto_indexes(self):
        value = packet([atom("自动索引 中文测试")])["atoms"][0]
        self.store.insert_atom(value)
        self.assertIn("自动", self.store.indexed_terms(value["id"]))

    def test_212_update_atom_auto_reindexes(self):
        value = packet([atom("old english")])["atoms"][0]
        self.store.insert_atom(value)
        self.store.update_atom(value["id"], {"canonical_statement": "new 中文内容"})
        self.assertIn("中文", self.store.indexed_terms(value["id"]))
        self.assertNotIn("old", self.store.indexed_terms(value["id"]))

    def test_213_packet_import_auto_indexes(self):
        value = packet([atom("候选记忆 candidate memory")])
        self.store.import_learning_packet(value)
        self.assertTrue(self.store.indexed_terms(value["atoms"][0]["id"]))

    def test_214_packet_import_is_idempotent(self):
        value = packet([atom("idempotent")])
        first = self.store.import_learning_packet(value)
        second = self.store.import_learning_packet(value)
        self.assertEqual((first["status"], second["status"]), ("IMPORTED", "IDEMPOTENT_DUPLICATE"))

    def test_215_import_creates_revision(self):
        result = self.store.import_learning_packet(packet([atom("revision")]))
        self.assertTrue(result["revision_id"].startswith("rev-"))

    def test_216_integrity_check_sees_automatic_index(self):
        self.store.import_learning_packet(packet([atom("indexed")]))
        self.assertTrue(self.store.integrity_check()["integrity_ok"])

    def test_217_chinese_bigrams_exist(self):
        terms = tokenize("确定性回放")
        self.assertIn("确定", terms)

    def test_218_chinese_trigrams_exist(self):
        terms = tokenize("确定性回放")
        self.assertIn("确定性", terms)

    def test_219_english_tokens_casefold(self):
        self.assertIn("vwap", tokenize("VWAP Research"))

    def test_220_mixed_query_retrieves(self):
        value = packet([atom("VWAP 候选 strategy research")])
        self.store.import_learning_packet(value)
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="VWAP 候选"))
        self.assertEqual(bundle.atoms[0]["id"], value["atoms"][0]["id"])

    def test_221_full_width_query_retrieves(self):
        value = packet([atom("VWAP research")])
        self.store.import_learning_packet(value)
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="ＶＷＡＰ"))
        self.assertEqual(len(bundle.atoms), 1)

    def test_222_empty_query_uses_structured_filters(self):
        self.store.import_learning_packet(packet([atom("A", scope="one"), atom("B", scope="two")]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="", scopes=("two",)))
        self.assertEqual([item["scope"] for item in bundle.atoms], ["two"])

    def test_223_type_filter_applies(self):
        self.store.import_learning_packet(packet([atom("same", atom_type="fact"), atom("same", atom_type="rule")]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="same", atom_types=("rule",)))
        self.assertTrue(all(item["atom_type"] == "rule" for item in bundle.atoms))

    def test_224_confidence_filter_applies(self):
        self.store.import_learning_packet(packet([atom("same", confidence=0.2), atom("same other", confidence=0.9)]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="same", min_confidence=0.8))
        self.assertTrue(all(item["confidence"] >= 0.8 for item in bundle.atoms))

    def test_225_rejected_truth_state_is_denied_in_plan(self):
        with self.assertRaisesRegex(ValueError, "truth_state"):
            QueryPlan(truth_states=("rejected",)).validate()

    def test_226_unknown_query_plan_field_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown_field"):
            QueryPlan.from_dict({"query_text": "x", "unexpected": True})

    def test_227_query_plan_round_trip(self):
        value = QueryPlan(query_text="x", scopes=("s",), relation_depth=2)
        self.assertEqual(QueryPlan.from_dict(value.to_dict()), value)

    def test_228_query_plan_hash_is_deterministic(self):
        self.assertEqual(QueryPlan(query_text="x").plan_hash, QueryPlan(query_text="x").plan_hash)

    def test_229_context_query_id_is_deterministic(self):
        self.store.import_learning_packet(packet([atom("x")]))
        assembler = ContextAssembler(self.store)
        self.assertEqual(assembler.assemble(QueryPlan(query_text="x")).query_id, assembler.assemble(QueryPlan(query_text="x")).query_id)

    def test_230_budget_omissions_are_reported(self):
        self.store.import_learning_packet(packet([atom("common one"), atom("common two"), atom("common three")]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="common", budget=1))
        self.assertEqual(len(bundle.omitted_due_to_budget), 2)

    def test_231_stable_tie_break_uses_id(self):
        self.store.import_learning_packet(packet([atom("common", scope="b"), atom("common", scope="a")]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="common"))
        self.assertEqual([item["id"] for item in bundle.atoms], sorted(item["id"] for item in bundle.atoms))

    def test_232_context_has_knowledge_version(self):
        self.store.import_learning_packet(packet([atom("version")]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="version"))
        self.assertTrue(bundle.knowledge_version.startswith("rev-"))

    def test_233_context_has_source_lineage(self):
        self.store.import_learning_packet(packet([atom("lineage")]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="lineage"))
        self.assertIn("evidence-test", bundle.source_lineage)

    def test_234_context_is_candidate_semantic_access(self):
        self.store.import_learning_packet(packet([atom("access")]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="access"))
        self.assertEqual(bundle.semantic_access_state, "FULL_SEMANTIC_ACCESS_CANDIDATE_ONLY")

    def test_235_case_a_no_conflict(self):
        self.store.import_learning_packet(packet([atom("fact one"), atom("fact two")]))
        self.assertEqual(self.store.stats()["conflicts"], 0)

    def test_236_case_b_explicit_conflict_preserved(self):
        left = atom_id("capital is Sydney", "fact", "geo")
        right = atom_id("capital is Canberra", "fact", "geo")
        value = packet([
            atom("capital is Sydney", scope="geo", id=left, knowledge_status="conflict"),
            atom("capital is Canberra", scope="geo", id=right, knowledge_status="conflict"),
        ], conflicts=[{"atom_id_a": left, "atom_id_b": right, "conflict_type": "DIRECT"}])
        self.store.import_learning_packet(value)
        self.assertEqual(self.store.stats()["conflicts"], 1)

    def test_237_case_c_supersedes_preserves_old(self):
        old = atom_id("old fact", "fact", "scope")
        new = atom_id("new fact", "fact", "scope")
        value = packet([
            atom("old fact", id=old, scope="scope"), atom("new fact", id=new, scope="scope")
        ], relations=[{"source_atom_id": new, "target_atom_id": old, "relation_type": "supersedes"}])
        self.store.import_learning_packet(value)
        self.assertEqual(self.store.get_atom(old)["knowledge_status"], "superseded")

    def test_238_case_d_correlation_remains_observation(self):
        value = packet([atom("X correlates with Y", atom_type="observation")])
        self.assertEqual(value["atoms"][0]["atom_type"], "observation")

    def test_239_case_e_restricted_atom_not_retrieved(self):
        value = packet([atom("restricted body", transport_visibility="RESTRICTED_NEVER_SYNC")])
        self.store.import_learning_packet(value)
        self.assertEqual(ContextAssembler(self.store).assemble(QueryPlan(query_text="restricted")).atoms, ())

    def test_240_case_f_multihop_relation_expansion(self):
        a, b, c = (atom_id(name, "fact", "chain") for name in ("alpha", "beta", "gamma"))
        value = packet([
            atom("alpha", id=a, scope="chain"), atom("beta", id=b, scope="chain"), atom("gamma", id=c, scope="chain")
        ], relations=[
            {"source_atom_id": a, "target_atom_id": b, "relation_type": "supports"},
            {"source_atom_id": b, "target_atom_id": c, "relation_type": "supports"},
        ])
        self.store.import_learning_packet(value)
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="alpha", relation_depth=2))
        self.assertEqual({item["id"] for item in bundle.atoms}, {a, b, c})

    def test_241_unknowns_are_preserved(self):
        value = packet([atom("known")])
        atom_key = value["atoms"][0]["id"]
        value = packet([atom("known", id=atom_key)], unknowns=[{"question": "unit?", "related_atom_ids": [atom_key]}])
        self.store.import_learning_packet(value)
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="known", include_unknowns=True))
        self.assertEqual(bundle.unknowns[0]["question"], "unit?")

    def test_242_conflicts_are_returned(self):
        left = atom_id("left", "fact")
        right = atom_id("right", "fact")
        value = packet([atom("left", id=left), atom("right", id=right)], conflicts=[{"atom_id_a": left, "atom_id_b": right}])
        self.store.import_learning_packet(value)
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="left", include_conflicts=True))
        self.assertEqual(len(bundle.conflicts), 1)

    def test_243_credential_value_field_is_rejected(self):
        value = packet([atom("safe")])
        value["credential_value"] = "nonempty-test-placeholder"
        with self.assertRaisesRegex(ValueError, "credential_value_denied"):
            self.store.import_learning_packet(value)

    def test_244_32_query_regression_passes_threshold(self):
        populate_retrieval_fixture(self.store)
        report = run_retrieval_regression(self.store)
        self.assertGreaterEqual(report["passed"], 30, report)

    def test_245_512_atom_scale_is_integrity_clean(self):
        atoms = [atom(f"synthetic scale atom {index} 规模测试", scope="scale") for index in range(512)]
        start = time.perf_counter()
        self.store.import_learning_packet(packet(atoms, source_hash="c" * 64))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="规模测试", budget=512))
        elapsed = time.perf_counter() - start
        self.assertEqual(len(bundle.atoms), 512)
        self.assertTrue(self.store.integrity_check()["integrity_ok"])
        self.assertGreaterEqual(elapsed, 0.0)

    def test_248_learning_packet_schema_validates(self):
        schema = json.loads((PHASE_ROOT / "schemas" / "LearningPacket.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, packet([atom("schema packet")]))

    def test_249_query_plan_schema_validates(self):
        schema = json.loads((PHASE_ROOT / "schemas" / "QueryPlan.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, QueryPlan(query_text="schema query").to_dict())

    def test_250_context_bundle_schema_validates(self):
        self.store.import_learning_packet(packet([atom("schema context")]))
        bundle = ContextAssembler(self.store).assemble(QueryPlan(query_text="schema context"))
        schema = json.loads((PHASE_ROOT / "schemas" / "ContextBundle.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, bundle.to_dict())


class SnapshotTestCase(unittest.TestCase):
    def test_246_snapshot_and_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "memory.sqlite"
            snapshot = root / "snapshot.sqlite"
            restored = root / "restored.sqlite"
            store = MemoryStore(original).connect()
            store.import_learning_packet(packet([atom("before snapshot")]))
            manifest = SnapshotManager.create(store, snapshot)
            store.import_learning_packet(packet([atom("after snapshot")], source_hash="d" * 64))
            store.close()
            SnapshotManager.restore(snapshot, restored, manifest["sha256"])
            restored_store = MemoryStore(restored).connect()
            try:
                self.assertEqual(restored_store.stats()["atoms"], 1)
            finally:
                restored_store.close()

    def test_247_snapshot_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = MemoryStore(root / "memory.sqlite").connect()
            snapshot = root / "snapshot.sqlite"
            SnapshotManager.create(store, snapshot)
            store.close()
            with self.assertRaisesRegex(ValueError, "snapshot_hash_mismatch"):
                SnapshotManager.restore(snapshot, root / "restored.sqlite", "0" * 64)


if __name__ == "__main__":
    unittest.main()
