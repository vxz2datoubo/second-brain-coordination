from __future__ import annotations

from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e59_runtime.mutations import MUTATION_SPECS, catalog_digest  # noqa: E402


class MutationRegistryTests(unittest.TestCase):
    def test_all_e58_audit_blockers_have_unique_mutations(self) -> None:
        blockers = {spec.blocker for spec in MUTATION_SPECS}
        self.assertEqual(len(MUTATION_SPECS), 9)
        self.assertEqual(len(blockers), 9)
        self.assertTrue(all(spec.mutation_id.startswith("E59-M") for spec in MUTATION_SPECS))

    def test_every_mutation_has_an_exact_target_and_named_oracle(self) -> None:
        for spec in MUTATION_SPECS:
            self.assertTrue(spec.original)
            self.assertTrue(spec.replacement)
            self.assertTrue(spec.test_selector.startswith("test_"))
            self.assertTrue(spec.invariant)

    def test_catalog_digest_is_deterministic(self) -> None:
        self.assertEqual(catalog_digest(), catalog_digest())
