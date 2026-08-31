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
            audit = creativectl.run(["--workspace", str(workspace), "audit"])
            self.assertEqual(audit["status"], "workspace_audit_verified")
            self.assertEqual(len(audit["evidence"]["verified_offline_generation_receipts"]), 1)
            self.assertEqual(len(audit["evidence"]["verified_feedback"]), 1)
            self.assertFalse(audit["evidence"]["canonical_knowledge_write"])

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

    def test_audit_rejects_feedback_that_no_longer_binds_to_a_verified_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            receipt_id = self.completed_workspace(workspace)
            saved = creativectl.run(["--workspace", str(workspace), "feedback", receipt_id, "3", "A source-bound note."])
            feedback_file = feedback_path(workspace, saved["feedback"]["feedback_id"])
            record = json.loads(feedback_file.read_text(encoding="utf-8"))
            record["source_timeline_hash"] = "0" * 64
            # Update the hash to make this a structurally valid but source-wrong
            # record; the audit must still catch the semantic mismatch.
            from creative_runtime.feedback import _feedback_hash

            record["feedback_hash"] = _feedback_hash(record)
            feedback_file.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(FeedbackViolation, "source binding"):
                creativectl.run(["--workspace", str(workspace), "audit"])


if __name__ == "__main__":
    unittest.main()
