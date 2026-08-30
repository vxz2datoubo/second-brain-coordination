from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.ledger import LedgerViolation
from creative_runtime.session import LOCK_DIRECTORY, SessionViolation


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_stale_frame_guard", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeStaleFrameGuardTests(unittest.TestCase):
    def test_expected_frame_id_allows_one_update_and_rejects_a_replayed_click(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "night_signal"])
            original = creativectl.run(["--workspace", str(workspace), "frame"])
            applied = creativectl.run(
                ["--workspace", str(workspace), "choose", "listen", "--expected-frame-id", original["frame_id"]]
            )
            before_stale_attempt = (workspace / "session.json").read_bytes()
            self.assertEqual(applied["prior_frame_id"], original["frame_id"])
            self.assertNotEqual(applied["current_frame_id"], original["frame_id"])
            with self.assertRaisesRegex(LedgerViolation, "Stale client frame"):
                creativectl.run(
                    ["--workspace", str(workspace), "choose", "listen", "--expected-frame-id", original["frame_id"]]
                )
            self.assertEqual((workspace / "session.json").read_bytes(), before_stale_attempt)
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "timeline"])["entries"].__len__(), 2)

    def test_busy_lock_and_stranded_atomic_temporary_fail_closed_without_mutating_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            session = workspace / "session.json"
            before = session.read_bytes()
            lock = workspace / LOCK_DIRECTORY / "default.lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text("simulated-other-owner\n", encoding="ascii")
            with self.assertRaisesRegex(SessionViolation, "busy"):
                creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            self.assertEqual(session.read_bytes(), before)
            lock.unlink()

            temporary = session.with_name(session.name + ".replace-tmp")
            temporary.write_text("interrupted replacement evidence\n", encoding="utf-8")
            with self.assertRaisesRegex(SessionViolation, "incomplete session replacement"):
                creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            self.assertEqual(session.read_bytes(), before)
            self.assertTrue(temporary.is_file())

    def test_free_text_passes_the_same_stale_frame_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            frame = creativectl.run(["--workspace", str(workspace), "frame"])
            result = creativectl.run(
                ["--workspace", str(workspace), "say", "listen carefully", "--expected-frame-id", frame["frame_id"]]
            )
            self.assertEqual(result["status"], "chosen")
            with self.assertRaisesRegex(LedgerViolation, "Stale client frame"):
                creativectl.run(
                    ["--workspace", str(workspace), "say", "approach carefully", "--expected-frame-id", frame["frame_id"]]
                )


if __name__ == "__main__":
    unittest.main()
