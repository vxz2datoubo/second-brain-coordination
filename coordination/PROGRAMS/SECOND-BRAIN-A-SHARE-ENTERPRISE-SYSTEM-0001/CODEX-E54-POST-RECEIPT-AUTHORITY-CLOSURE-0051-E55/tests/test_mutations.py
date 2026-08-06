from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from e55_authority.mutations import MUTATION_SPECS, run_production_source_mutations  # noqa: E402


class ProductionSourceMutationTests(unittest.TestCase):
    def test_each_registered_production_mutation_is_killed_and_restored(self) -> None:
        results = run_production_source_mutations(ROOT / "src" / "e55_authority", ROOT / "tests")
        self.assertEqual([item.mutation_id for item in results], [item.mutation_id for item in MUTATION_SPECS])
        self.assertTrue(all(item.replacement_count == 1 for item in results))
        self.assertTrue(all(item.mutated_exit_code != 0 and item.restored_exit_code == 0 for item in results))
        self.assertTrue(all(item.pristine_sha256 == item.restored_sha256 for item in results))
        self.assertTrue(all(item.mutated_duration_ns > 0 and item.restored_duration_ns > 0 for item in results))


if __name__ == "__main__":
    unittest.main()
