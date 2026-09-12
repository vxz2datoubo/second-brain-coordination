"""Acceptance tests for the shadow cognitive loop (v0)."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

_TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from cognitive_loop import (  # noqa: E402
    ShadowStore,
    detect_conflicts,
    ingest,
    reason,
    retrieve,
    record_prediction,
    apply_outcome,
)
from cognitive_loop.benchmark import run_benchmark  # noqa: E402
from cognitive_loop.atom import KnowledgeAtom, Provenance  # noqa: E402

NOW = "2099-01-01T00:00:00+00:00"


def _provenance(**kwargs):
    defaults = dict(source_type="user_statement", retriever="workbuddy", retrieved_at=NOW)
    defaults.update(kwargs)
    return Provenance(**defaults)


class AtomTests(unittest.TestCase):
    def test_atom_id_is_content_addressed(self) -> None:
        a = KnowledgeAtom("甲", "s", "t", "fact", 0.9, _provenance(), NOW)
        b = KnowledgeAtom("甲", "s", "t", "fact", 0.9, _provenance(), NOW)
        c = KnowledgeAtom("乙", "s", "t", "fact", 0.9, _provenance(), NOW)
        self.assertEqual(a.atom_id, b.atom_id)
        self.assertNotEqual(a.atom_id, c.atom_id)

    def test_time_validity_filters_stale(self) -> None:
        atom = KnowledgeAtom("甲", "s", "t", "fact", 0.9, _provenance(), "2020-01-01", time_valid_to="2021-01-01")
        self.assertFalse(atom.is_time_valid("2026-01-01"))
        self.assertTrue(atom.is_time_valid("2020-06-01"))

    def test_confidence_must_be_bounded(self) -> None:
        with self.assertRaises(ValueError):
            KnowledgeAtom("甲", "s", "t", "fact", 1.5, _provenance(), NOW)
        with self.assertRaises(ValueError):
            KnowledgeAtom("甲", "s", "t", "fact", -0.1, _provenance(), NOW)

    def test_nature_must_be_known(self) -> None:
        with self.assertRaises(ValueError):
            KnowledgeAtom("甲", "s", "t", "hallucination", 0.9, _provenance(), NOW)


class StoreTests(unittest.TestCase):
    def test_upsert_and_get_roundtrip(self) -> None:
        store = ShadowStore(":memory:")
        atom = ingest(store, content="主营业务是AI", subject="星光科技", topic="主营业务", confidence=0.9)
        got = store.get_atom(atom.atom_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.content, "主营业务是AI")
        store.close()

    def test_list_filters_by_topic(self) -> None:
        store = ShadowStore(":memory:")
        ingest(store, content="甲", subject="s", topic="业务")
        ingest(store, content="乙", subject="s", topic="估值")
        self.assertEqual(len(store.list_atoms(topic="业务")), 1)
        self.assertEqual(len(store.all_atoms()), 2)
        store.close()


class RetrieveTests(unittest.TestCase):
    def _store_with_corpus(self) -> ShadowStore:
        store = ShadowStore(":memory:")
        ingest(store, content="星光科技主营业务是AI视频生成", subject="星光科技", topic="主营业务", confidence=0.9)
        ingest(store, content="星光科技已经上市", subject="星光科技", topic="上市状态", confidence=0.95)
        ingest(store, content="另一个公司做电商", subject="另一个公司", topic="主营业务", confidence=0.9)
        return store

    def test_retrieve_ranks_matching_subject_first(self) -> None:
        store = self._store_with_corpus()
        results = retrieve(store.all_atoms(), "星光科技主营业务", NOW, top_k=3)
        self.assertTrue(results)
        self.assertEqual(results[0].atom.subject, "星光科技")
        store.close()

    def test_retrieve_filters_stale_atoms(self) -> None:
        store = ShadowStore(":memory:")
        ingest(store, content="旧业务", subject="星光科技", topic="业务",
               time_valid_to="2020-01-01T00:00:00+00:00")
        results = retrieve(store.all_atoms(), "星光科技业务", NOW)
        self.assertEqual(results, [])
        store.close()

    def test_detect_conflicts_surfaces_disagreement(self) -> None:
        store = ShadowStore(":memory:")
        ingest(store, content="CEO是李明", subject="星光科技", topic="CEO")
        ingest(store, content="CEO是王强", subject="星光科技", topic="CEO")
        conflicts = detect_conflicts(store.all_atoms())
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].topic, "CEO")
        store.close()


class ReasonTests(unittest.TestCase):
    def test_reason_returns_fact_with_confidence(self) -> None:
        store = ShadowStore(":memory:")
        ingest(store, content="星光科技主营业务是AI视频生成", subject="星光科技", topic="主营业务", confidence=0.9)
        answer = reason(store.all_atoms(), "星光科技主营业务是什么", NOW)
        self.assertEqual(answer.answer, "星光科技主营业务是AI视频生成")
        self.assertGreater(answer.confidence, 0.0)
        store.close()

    def test_reason_no_evidence_gives_caveat(self) -> None:
        store = ShadowStore(":memory:")
        answer = reason(store.all_atoms(), "完全无关的问题", NOW)
        self.assertIsNone(answer.answer)
        self.assertIn("no time-valid evidence found", answer.caveats)
        store.close()

    def test_reason_flags_conflict(self) -> None:
        store = ShadowStore(":memory:")
        ingest(store, content="CEO是李明", subject="星光科技", topic="CEO", confidence=0.9)
        ingest(store, content="CEO是王强", subject="星光科技", topic="CEO", confidence=0.8)
        answer = reason(store.all_atoms(), "星光科技CEO是谁", NOW)
        self.assertGreater(answer.contradicting_count, 0)
        store.close()


class FeedbackTests(unittest.TestCase):
    def test_correct_outcome_raises_confidence(self) -> None:
        store = ShadowStore(":memory:")
        ingest(store, content="主营业务是AI", subject="星光科技", topic="主营业务", confidence=0.5)
        fid = record_prediction(store, "主营是什么", "星光科技", "主营业务是AI", 0.5)
        outcome = apply_outcome(store, fid, "星光科技", "主营业务是AI", NOW)
        self.assertTrue(outcome.was_correct)
        self.assertGreater(outcome.updated_atoms[0].confidence, 0.5)
        store.close()

    def test_wrong_outcome_lowers_confidence(self) -> None:
        store = ShadowStore(":memory:")
        ingest(store, content="主营业务是AI", subject="星光科技", topic="主营业务", confidence=0.9)
        fid = record_prediction(store, "主营是什么", "星光科技", "主营业务是AI", 0.9)
        outcome = apply_outcome(store, fid, "星光科技", "主营业务是别的", NOW)
        self.assertFalse(outcome.was_correct)
        self.assertLess(outcome.updated_atoms[0].confidence, 0.9)
        store.close()


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_closes_all_four_loops(self) -> None:
        report = run_benchmark()
        self.assertEqual(report["retrieval"]["hits"], report["retrieval"]["total"])
        self.assertEqual(report["reasoning"]["hits"], report["reasoning"]["total"])
        self.assertEqual(report["conflict_detection"]["hits"], 1)
        self.assertEqual(report["feedback_loop"]["hits"], 1)
        self.assertEqual(report["total_hits"], report["total_questions"])


if __name__ == "__main__":
    unittest.main()
