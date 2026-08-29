from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.knowledge import KnowledgeBridgeViolation, KnowledgeReviewBridge


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_s04", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeS04KnowledgeTests(unittest.TestCase):
    def test_candidate_requires_provenance_and_cannot_write_canonical_knowledge(self) -> None:
        bridge = KnowledgeReviewBridge()
        with self.assertRaises(KnowledgeBridgeViolation):
            bridge.correct("A claim without evidence")
        candidate = bridge.correct("Listening first reduces uncertainty.", source_event_ids=("evt_001",))
        self.assertEqual(candidate.status, "pending_human_review")
        self.assertFalse(bridge.canonical_write_enabled)
        self.assertEqual(bridge.search("uncertainty"), [candidate])

    def test_only_named_non_executor_review_can_approve_candidate(self) -> None:
        bridge = KnowledgeReviewBridge()
        candidate = bridge.correct("Use daylight for a follow-up.", source_artifact_ids=("art_001",))
        with self.assertRaises(KnowledgeBridgeViolation):
            bridge.review(candidate.candidate_id, "CODEX", True, "self review")
        reviewed = bridge.review(candidate.candidate_id, "HUMAN_REVIEWER", True, "Checked source trace")
        self.assertEqual(reviewed.status, "approved_reusable_candidate")
        self.assertEqual(reviewed.reviewer, "HUMAN_REVIEWER")

    def test_cli_knowledge_commands_persist_review_packet_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            created = creativectl.run([
                "--workspace", str(workspace), "knowledge", "correct", "Keep a consequence visible.", "--source-event-id", "evt_001",
            ])
            candidate_id = created["candidate"]["candidate_id"]
            found = creativectl.run(["--workspace", str(workspace), "knowledge", "search", "consequence"])
            reviewed = creativectl.run([
                "--workspace", str(workspace), "knowledge", "review", candidate_id, "--reviewer", "HUMAN_REVIEWER", "--approve", "--note", "approved",
            ])
            self.assertEqual(found["candidates"][0]["candidate_id"], candidate_id)
            self.assertTrue(reviewed["candidate"]["status"].startswith("approved"))
            self.assertFalse(reviewed["canonical_write"])


if __name__ == "__main__":
    unittest.main()
