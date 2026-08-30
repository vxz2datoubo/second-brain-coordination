from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.sequence import SequenceViolation, build_verified_sequence
from creative_runtime.ledger import CreativeLedger


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_sequence", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeSequenceTests(unittest.TestCase):
    def test_sequence_reconstructs_prefixes_and_reestablishes_space_on_scene_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            prefix = ["--workspace", str(workspace), "--slot", "night_cut"]
            creativectl.run([*prefix, "init", "--scenario", "night_signal"])
            creativectl.run([*prefix, "choose", "listen"])
            creativectl.run([*prefix, "choose", "approach"])
            plan = build_verified_sequence(creativectl._load_session(workspace, "night_cut"), slot="night_cut").to_dict()
            self.assertEqual(plan["status"], "sequence_plan_verified")
            self.assertEqual(len(plan["steps"]), 3)
            self.assertEqual(plan["steps"][0]["cut_policy"], "establish_initial_space")
            self.assertEqual(plan["steps"][1]["cut_policy"], "hold_verified_axis")
            self.assertEqual(plan["steps"][2]["cut_policy"], "reestablish_after_scene_change")
            self.assertEqual(plan["steps"][2]["state"]["scene_id"], "signal_room")
            self.assertTrue(all(step["shots"] for step in plan["steps"]))
            self.assertGreater(plan["total_duration_seconds"], 0)

    def test_sequence_refuses_empty_ledger(self) -> None:
        with self.assertRaisesRegex(SequenceViolation, "verified story timeline"):
            build_verified_sequence(CreativeLedger())


if __name__ == "__main__":
    unittest.main()
