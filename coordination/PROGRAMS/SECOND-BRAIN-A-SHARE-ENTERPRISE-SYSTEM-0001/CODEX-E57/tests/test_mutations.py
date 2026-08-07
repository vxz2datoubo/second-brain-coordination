from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.mutations import CATALOG, catalog_digest, run_catalog


class GenuineMutationTests(unittest.TestCase):
    def test_catalog_has_unique_ids_and_targets(self) -> None:
        contract = json.loads((TASK_ROOT / "PROVIDER-CONTRACT.json").read_text(encoding="utf-8"))
        self.assertEqual(tuple(item.mutation_id for item in CATALOG), tuple(contract["evaluation"]["mutation_ids"]))
        self.assertEqual(len({item.mutation_id for item in CATALOG}), len(CATALOG))
        self.assertEqual(len({(item.relative_path, item.old) for item in CATALOG}), len(CATALOG))

    def test_catalog_is_deterministically_identified(self) -> None:
        self.assertEqual(catalog_digest(), catalog_digest())
        self.assertEqual(len(catalog_digest()), 64)

    def test_every_mutation_changes_fails_and_restores(self) -> None:
        results = run_catalog(TASK_ROOT)
        self.assertEqual(len(results), len(CATALOG))
        for result in results:
            with self.subTest(result.mutation_id):
                self.assertTrue(result.changed)
                self.assertTrue(result.named_invariant_failed)
                self.assertTrue(result.restored_exactly)
                self.assertNotEqual(result.before_sha256, result.mutated_sha256)
                self.assertEqual(result.before_sha256, result.restored_sha256)
