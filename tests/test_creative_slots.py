from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.generation import GenerationViolation, offline_generation_receipt_path
from creative_runtime.session import SessionViolation, legacy_session_path, v2_session_path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_slots", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


def command(workspace: Path, slot: str, *arguments: str) -> list[str]:
    return ["--workspace", str(workspace), "--slot", slot, *arguments]


class CreativeSlotTests(unittest.TestCase):
    def test_slots_keep_story_migration_generation_feedback_and_audit_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(command(workspace, "default", "init"))
            creativectl.run(command(workspace, "route_b", "init", "--scenario", "three_scene"))
            creativectl.run(command(workspace, "route_b", "choose", "listen"))
            creativectl.run(command(workspace, "route_b", "choose", "approach"))
            creativectl.run(command(workspace, "route_b", "choose", "listen"))

            default_view = creativectl.run(command(workspace, "default", "play"))
            route_view = creativectl.run(command(workspace, "route_b", "play"))
            self.assertEqual(default_view["state"]["scene_id"], "synthetic_archive")
            self.assertEqual(route_view["state"]["scene_id"], "interior_archive")
            self.assertEqual(route_view["slot_id"], "route_b")
            self.assertEqual(legacy_session_path(workspace), workspace / "session.json")
            self.assertEqual(legacy_session_path(workspace, "route_b"), workspace / "slots" / "route_b.json")

            generated = creativectl.run(command(workspace, "route_b", "generate-offline"))
            receipt_id = generated["receipt"]["receipt_id"]
            self.assertEqual(generated["receipt"]["source"]["slot_id"], "route_b")
            self.assertTrue(offline_generation_receipt_path(workspace, receipt_id, "route_b").is_file())
            self.assertFalse(offline_generation_receipt_path(workspace, receipt_id).exists())
            with self.assertRaisesRegex(GenerationViolation, "does not exist"):
                creativectl.run(command(workspace, "default", "verify-generation", receipt_id))

            feedback = creativectl.run(command(workspace, "route_b", "feedback", receipt_id, "5", "The handoff consequence is clear."))
            self.assertEqual(feedback["feedback"]["slot_id"], "route_b")
            self.assertTrue((workspace / "knowledge-review" / "route_b.json").is_file())
            migration = creativectl.run(command(workspace, "route_b", "migrate"))
            self.assertEqual(migration["slot_id"], "route_b")
            self.assertTrue(v2_session_path(workspace, "route_b").is_file())
            self.assertFalse(v2_session_path(workspace).exists())
            self.assertEqual(creativectl.run(command(workspace, "route_b", "verify-v2"))["slot_id"], "route_b")

            route_audit = creativectl.run(command(workspace, "route_b", "audit"))
            default_audit = creativectl.run(command(workspace, "default", "audit"))
            self.assertEqual(route_audit["story"]["slot_id"], "route_b")
            self.assertEqual(len(route_audit["evidence"]["verified_offline_generation_receipts"]), 1)
            self.assertEqual(len(route_audit["evidence"]["verified_feedback"]), 1)
            self.assertEqual(len(default_audit["evidence"]["verified_offline_generation_receipts"]), 0)
            self.assertEqual(len(default_audit["evidence"]["verified_feedback"]), 0)

    def test_slot_name_cannot_escape_the_workspace_or_create_files(self) -> None:
        invalid_slots = ("../outside", "..", "route/b", "UPPER", "", "a" * 33)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            for slot in invalid_slots:
                with self.assertRaisesRegex(SessionViolation, "Slot must match"):
                    creativectl.run(command(workspace, slot, "init"))
            self.assertEqual(list(workspace.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
