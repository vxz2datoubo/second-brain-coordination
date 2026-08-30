from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.generation import GenerationViolation, offline_generation_receipt_path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_generation_receipts", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeGenerationReceiptTests(unittest.TestCase):
    def completed_workspace(self, workspace: Path) -> None:
        creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])
        creativectl.run(["--workspace", str(workspace), "choose", "approach"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])

    def test_offline_generation_receipt_is_deterministic_source_bound_and_read_only_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self.completed_workspace(workspace)

            first = creativectl.run(["--workspace", str(workspace), "generate-offline"])
            receipt_id = first["receipt"]["receipt_id"]
            target = offline_generation_receipt_path(workspace, receipt_id)
            before = target.read_bytes()
            second = creativectl.run(["--workspace", str(workspace), "generate-offline"])
            verified = creativectl.run(["--workspace", str(workspace), "verify-generation", receipt_id])

            self.assertEqual(first["status"], "offline_generation_recorded")
            self.assertEqual(second["status"], "offline_generation_already_recorded")
            self.assertEqual(first["receipt"], second["receipt"])
            self.assertEqual(first["receipt"]["result"]["provider"], "offline")
            self.assertTrue(first["receipt"]["result"]["simulated"])
            self.assertTrue(first["receipt"]["result"]["output_ref"].startswith("offline://"))
            self.assertEqual(verified["status"], "offline_generation_verified")
            self.assertEqual(verified["receipt"], first["receipt"])
            self.assertEqual(target.read_bytes(), before)

    def test_generation_receipt_rejects_tampering_and_story_drift_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self.completed_workspace(workspace)
            generated = creativectl.run(["--workspace", str(workspace), "generate-offline"])
            receipt_id = generated["receipt"]["receipt_id"]
            target = offline_generation_receipt_path(workspace, receipt_id)
            clean_receipt = target.read_bytes()
            record = json.loads(target.read_text(encoding="utf-8"))
            record["quality_metrics"]["shot_count"] = 999
            target.write_text(json.dumps(record), encoding="utf-8")
            tampered = target.read_bytes()

            with self.assertRaisesRegex(GenerationViolation, "hash"):
                creativectl.run(["--workspace", str(workspace), "verify-generation", receipt_id])
            self.assertEqual(target.read_bytes(), tampered)

            # A separately valid receipt is also bound to its source timeline.
            # Rebuild cleanly, then advance the story before asking to verify it.
            target.write_bytes(clean_receipt)
            creativectl.run(["--workspace", str(workspace), "choose", "leave"])
            with self.assertRaisesRegex(GenerationViolation, "does not match the current verified story source"):
                creativectl.run(["--workspace", str(workspace), "verify-generation", receipt_id])
            self.assertEqual(target.read_bytes(), clean_receipt)

    def test_unknown_shot_is_rejected_before_a_generation_receipt_directory_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self.completed_workspace(workspace)
            with self.assertRaisesRegex(GenerationViolation, "Requested shot"):
                creativectl.run(["--workspace", str(workspace), "generate-offline", "--shot-id", "not-a-shot"])
            self.assertFalse((workspace / "generation-receipts").exists())


if __name__ == "__main__":
    unittest.main()
