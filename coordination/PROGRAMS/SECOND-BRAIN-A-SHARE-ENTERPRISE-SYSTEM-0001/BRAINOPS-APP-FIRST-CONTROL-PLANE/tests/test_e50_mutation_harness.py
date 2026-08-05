"""The E50 mutation registry must prove its named tests go red."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.e50_mutation_harness import run_e50_mutation_harness  # noqa: E402


class E50MutationHarnessTests(unittest.TestCase):
    def test_all_required_mutations_are_killed(self):
        observations = run_e50_mutation_harness(PROGRAM_ROOT)
        self.assertGreaterEqual(len(observations), 12)
        self.assertTrue(all(item.killed for item in observations))
        self.assertEqual(len({item.mutation_id for item in observations}), len(observations))
        self.assertTrue(all(item.output_sha256 for item in observations))
