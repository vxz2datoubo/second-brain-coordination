from __future__ import annotations

from pathlib import Path
import unittest

from e54_authority import MUTATION_SPECS, run_mutation_matrix


class CopiedProductionMutationTests(unittest.TestCase):
    def test_every_registered_mutation_is_killed_and_restored(self) -> None:
        root = Path(__file__).resolve().parents[1]
        results = run_mutation_matrix(root / "src" / "e54_authority", root / "tests")
        self.assertEqual([item.mutation_id for item in results], [item.mutation_id for item in MUTATION_SPECS])
        self.assertTrue(all(item.mutated_exit_code != 0 for item in results))
        self.assertTrue(all(item.restored_exit_code == 0 for item in results))
        self.assertTrue(all(item.pristine_sha256 == item.restored_source_sha256 for item in results))


if __name__ == "__main__":
    unittest.main()
