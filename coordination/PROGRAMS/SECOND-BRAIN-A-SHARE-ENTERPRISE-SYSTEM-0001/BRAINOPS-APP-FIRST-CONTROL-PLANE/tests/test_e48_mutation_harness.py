"""The E48 mutation harness must execute changed code and observe red gates."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROGRAM_ROOT.parents[3]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.mutation_harness import run_active_mutation_harness  # noqa: E402


class E48MutationHarnessTests(unittest.TestCase):
    def test_all_required_mutations_execute_and_are_killed(self):
        head = subprocess.check_output(
            ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        observations = run_active_mutation_harness(
            PROGRAM_ROOT,
            REPOSITORY_ROOT,
            "ac17da81cd2ea019786e9f1d229eaede944756d9",
            head,
        )
        self.assertEqual(len(observations), 14)
        self.assertTrue(all(item.killed for item in observations))
        self.assertTrue(all(len(item.output_sha256) == 64 for item in observations))
