from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.generation import GenerationViolation, _digest_record, offline_generation_receipt_path
from creative_runtime.continuity import GraphBeat, GraphTransition, StoryGraph, TimelineViolation
from creative_runtime.knowledge import KnowledgeBridgeViolation
from creative_runtime.ledger import LedgerViolation
from creative_runtime.session import SessionViolation, load_v2_session, migrate_legacy_session, v2_session_path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_input_boundaries", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeInputBoundaryTests(unittest.TestCase):
    def test_story_graph_rejects_non_explicit_boundary_violations_before_they_become_playable(self) -> None:
        safe_beat = GraphBeat("safe", "arrival", "Two adult archivists pause at a public archive door.")
        unsafe_beat = GraphBeat("unsafe", "arrival", "A graphic sexual scene is described.")
        with self.assertRaisesRegex(TimelineViolation, "non_explicit"):
            StoryGraph("UnsafeBeatGraph/v1", (safe_beat, unsafe_beat), ())
        unsafe_label = GraphTransition("tr_unsafe", "safe", "arrival", "listen", "Show gore in detail", {"beat_id": "arrival"})
        with self.assertRaisesRegex(TimelineViolation, "non_explicit"):
            StoryGraph("UnsafeLabelGraph/v1", (safe_beat,), (unsafe_label,))

    def test_malformed_session_roots_fail_closed_without_creating_a_shadow_save(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            session = workspace / "session.json"
            session.write_text("[]", encoding="utf-8")
            before = session.read_bytes()
            with self.assertRaisesRegex(LedgerViolation, "root"):
                creativectl.run(["--workspace", str(workspace), "replay"])
            self.assertEqual(session.read_bytes(), before)
            self.assertFalse((workspace / "saves").exists())

            session.write_text(json.dumps({"schema": "CreativeSession/v1", "events": "not-a-list"}), encoding="utf-8")
            before = session.read_bytes()
            with self.assertRaisesRegex(LedgerViolation, "events"):
                creativectl.run(["--workspace", str(workspace), "play"])
            self.assertEqual(session.read_bytes(), before)

    def test_malformed_knowledge_packet_is_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            packet = workspace / "knowledge-review.json"
            packet.write_text("[]", encoding="utf-8")
            before = packet.read_bytes()
            with self.assertRaisesRegex(KnowledgeBridgeViolation, "schema"):
                creativectl.run(["--workspace", str(workspace), "knowledge", "search", "anything"])
            self.assertEqual(packet.read_bytes(), before)

    def test_malformed_v2_count_and_receipt_shape_fail_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            creativectl.run(["--workspace", str(workspace), "choose", "approach"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            migrate_legacy_session(workspace, "2030-01-01T00:03:00Z")
            v2 = v2_session_path(workspace)
            v2_record = json.loads(v2.read_text(encoding="utf-8"))
            v2_record["migration"]["legacy_event_count"] = "4"
            v2.write_text(json.dumps(v2_record), encoding="utf-8")
            v2_before = v2.read_bytes()
            with self.assertRaisesRegex(SessionViolation, "event count is malformed"):
                load_v2_session(workspace)
            self.assertEqual(v2.read_bytes(), v2_before)

            # A new workspace keeps the generation-source route valid so the
            # receipt boundary can be tested independently of the v2 defect.
            other = workspace / "other"
            creativectl.run(["--workspace", str(other), "init", "--scenario", "three_scene"])
            creativectl.run(["--workspace", str(other), "choose", "listen"])
            creativectl.run(["--workspace", str(other), "choose", "approach"])
            creativectl.run(["--workspace", str(other), "choose", "listen"])
            generated = creativectl.run(["--workspace", str(other), "generate-offline"])
            receipt_path = offline_generation_receipt_path(other, generated["receipt"]["receipt_id"])
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            del receipt["quality_metrics"]
            receipt["receipt_hash"] = _digest_record(receipt)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            receipt_before = receipt_path.read_bytes()
            with self.assertRaisesRegex(GenerationViolation, "required fields"):
                creativectl.run(["--workspace", str(other), "verify-generation", generated["receipt"]["receipt_id"]])
            self.assertEqual(receipt_path.read_bytes(), receipt_before)


if __name__ == "__main__":
    unittest.main()
