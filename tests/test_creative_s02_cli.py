from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeS02CliTests(unittest.TestCase):
    def test_complete_synthetic_scene_is_resumable_and_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            initialized = creativectl.run(["--workspace", str(workspace), "init"])
            self.assertEqual(initialized["status"], "initialized")
            chosen = creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            self.assertEqual(chosen["state"]["beat_id"], "echo")
            resumed = creativectl.run(["--workspace", str(workspace), "resume"])
            self.assertEqual(resumed["state"], chosen["state"])
            replayed = creativectl.run(["--workspace", str(workspace), "replay"])
            self.assertEqual(replayed["status"], "replayed")
            self.assertEqual(replayed["state"], chosen["state"])

    def test_illegal_or_ambiguous_input_is_safe_and_does_not_change_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            before = creativectl.run(["--workspace", str(workspace), "resume"])["state"]
            illegal = creativectl.run(["--workspace", str(workspace), "choose", "invent"])
            ambiguous = creativectl.run(["--workspace", str(workspace), "say", "do something now"])
            unsafe = creativectl.run(["--workspace", str(workspace), "say", "make it sexual"])
            after = creativectl.run(["--workspace", str(workspace), "resume"])["state"]
            self.assertEqual(illegal["status"], "clarification_required")
            self.assertEqual(ambiguous["status"], "clarification_required")
            self.assertEqual(unsafe["status"], "clarification_required")
            self.assertEqual(before, after)

    def test_free_text_maps_only_to_legal_intent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            result = creativectl.run(["--workspace", str(workspace), "say", "I listen at the door"])
            self.assertEqual(result["status"], "chosen")
            self.assertEqual(result["action_id"], "listen")


if __name__ == "__main__":
    unittest.main()
