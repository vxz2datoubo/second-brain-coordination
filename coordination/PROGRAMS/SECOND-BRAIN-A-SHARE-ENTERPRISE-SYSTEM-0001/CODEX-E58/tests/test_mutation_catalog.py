from __future__ import annotations

from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e58_runtime.mutations import MUTATION_SPECS, REQUIRED_AUDIT_BLOCKERS, catalog_digest  # noqa: E402


class MutationCatalogTests(unittest.TestCase):
    def test_all_e57_semantic_review_blockers_have_a_genuine_mutation(self) -> None:
        self.assertEqual(
            REQUIRED_AUDIT_BLOCKERS,
            {
                "E57-B1-CALLER-AUTHORED-EVALUATOR-RECEIPT",
                "E57-B2-NON-OPPOSING-CONFLICT",
                "E57-B3-CIRCULAR-RELATION-EVIDENCE",
                "E57-B4-UNVERIFIED-REDACTION-POLICY",
                "E57-B5-NO-PUBLIC-VERIFIER-ONLY-CAPABILITY",
                "E57-B6-JSONL-WHOLE-SOURCE-OWNERSHIP-INCOMPLETE",
                "E57-B7-SURROGATE-EDGE-NOT-CLOSED",
            },
        )

    def test_mutation_ids_are_unique_and_catalog_is_deterministic(self) -> None:
        identifiers = [item.mutation_id for item in MUTATION_SPECS]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(catalog_digest(), catalog_digest())

    def test_every_mutation_declares_a_target_test_and_exact_replacement(self) -> None:
        for item in MUTATION_SPECS:
            self.assertTrue(item.original)
            self.assertTrue(item.replacement)
            self.assertTrue(item.test_selector.startswith("tests."))
            self.assertTrue(item.invariant)
