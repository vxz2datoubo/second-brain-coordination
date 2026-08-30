from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.feedback import FeedbackViolation, feedback_path, load_feedback
from creative_runtime.generation import GenerationViolation, offline_generation_receipt_path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_feedback", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeFeedbackTests(unittest.TestCase):
    def completed_workspace(self, workspace: Path) -> str:
        creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])
        creativectl.run(["--workspace", str(workspace), "choose", "approach"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])
        return creativectl.run(["--workspace", str(workspace), "generate-offline"])["receipt"]["receipt_id"]

    def test_feedback_is_source_bound_idempotent_and_only_creates_pending_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            receipt_id = self.completed_workspace(workspace)
            first = creativectl.run(
                ["--workspace", str(workspace), "feedback", receipt_id, "4", "The camera keeps the established axis clear."]
            )
            feedback_id = first["feedback"]["feedback_id"]
            target = feedback_path(workspace, feedback_id)
            before = target.read_bytes()
            second = creativectl.run(
                ["--workspace", str(workspace), "feedback", receipt_id, "4", "The camera keeps the established axis clear."]
            )

            self.assertEqual(first["status"], "feedback_recorded")
            self.assertEqual(second["status"], "feedback_already_recorded")
            self.assertEqual(first["feedback"], second["feedback"])
            self.assertEqual(first["feedback"]["rating"], 4)
            self.assertEqual(first["knowledge_candidate"]["status"], "pending_human_review")
            self.assertFalse(first["canonical_write"])
            self.assertEqual(load_feedback(workspace, feedback_id).feedback_hash, first["feedback"]["feedback_hash"])
            self.assertEqual(target.read_bytes(), before)

    def test_feedback_rejects_bad_rating_tampered_source_and_does_not_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            receipt_id = self.completed_workspace(workspace)
            with self.assertRaisesRegex(FeedbackViolation, "0 through 5"):
                creativectl.run(["--workspace", str(workspace), "feedback", receipt_id, "6", "Too high."])
            self.assertFalse((workspace / "feedback").exists())

            receipt_path = offline_generation_receipt_path(workspace, receipt_id)
            receipt_record = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt_record["result"]["status"] = "not-simulated"
            receipt_path.write_text(json.dumps(receipt_record), encoding="utf-8")
            tampered = receipt_path.read_bytes()
            with self.assertRaisesRegex(GenerationViolation, "hash"):
                creativectl.run(["--workspace", str(workspace), "feedback", receipt_id, "3", "Check source first."])
            self.assertEqual(receipt_path.read_bytes(), tampered)
            self.assertFalse((workspace / "feedback").exists())


if __name__ == "__main__":
    unittest.main()
