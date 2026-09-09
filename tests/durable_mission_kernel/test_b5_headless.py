"""B5 tests — headless adapter, runtime/model attestation, context rollover."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.durable_mission_kernel import headless  # noqa: E402


class B5HeadlessTests(unittest.TestCase):
    def test_attestation_captures_runtime(self):
        att = headless.attest_runtime(model_id="deepseek-v4-pro")
        self.assertTrue(att.python_version)
        self.assertEqual(att.platform, sys.platform)
        self.assertEqual(att.model_id, "deepseek-v4-pro")
        self.assertEqual(att.model_profile, "DEEP_ENGINEERING")

    def test_context_rollover_roundtrip(self):
        adapter = headless.HeadlessAdapter("m1", headless.attest_runtime())
        ro = adapter.rollover("CHECKPOINTED", 5, "resume episode",
                              verified_facts={"head": "abc123"}, exact_git_head="abc123")
        raw = ro.to_json()
        back = headless.ContextRollover.from_json(raw)
        self.assertEqual(back.mission_id, "m1")
        self.assertEqual(back.state, "CHECKPOINTED")
        self.assertEqual(back.state_seq, 5)
        self.assertEqual(back.next_action, "resume episode")
        self.assertEqual(back.exact_git_head, "abc123")

    def test_launch_episode_record(self):
        adapter = headless.HeadlessAdapter("m1", headless.attest_runtime(model_id="m"))
        rec = adapter.launch_episode("ep1")
        self.assertEqual(rec["episode_id"], "ep1")
        self.assertEqual(rec["mission_id"], "m1")
        self.assertIn("attestation", rec)
        self.assertIsNone(rec["resume_from"])


if __name__ == "__main__":
    unittest.main()
