from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "create_creative_quota_checkpoint",
    ROOT / "tools" / "create_creative_quota_checkpoint.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class QuotaCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self._git("init", "-b", "codex/example")
        self._git("config", "user.email", "codex@example.invalid")
        self._git("config", "user.name", "Codex Test")
        (self.repo / ".gitignore").write_text(".creative-evidence/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "fixture [agent:CODEX]")
        self.head = self._git("rev-parse", "HEAD")
        self.remote_ref = "refs/remotes/origin/codex/checkpoint-example"
        self._git("update-ref", self.remote_ref, self.head)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()

    def _build(self, **overrides):
        kwargs = {
            "repo": self.repo,
            "source_agent": "CODEX",
            "target_agent": "WORKBUDDY",
            "baseline": self.head,
            "checkpoint_remote_ref": self.remote_ref,
            "remaining_next_action": "WorkBuddy runs exact-head reproduction.",
            "tests": ["creative_suite=PASS", "posix_only=SKIP"],
            "completed_scope": ["relay infrastructure"],
        }
        kwargs.update(overrides)
        return MODULE.build_checkpoint(**kwargs)

    def test_clean_exact_remote_checkpoint_passes(self) -> None:
        payload = self._build()
        self.assertEqual(payload["exact_head"], self.head)
        self.assertTrue(payload["buildable"])
        self.assertFalse(payload["final_acceptance"])

    def test_dirty_worktree_fails(self) -> None:
        (self.repo / "dirty.txt").write_text("dirty", encoding="utf-8")
        with self.assertRaisesRegex(MODULE.CheckpointError, "worktree must be clean"):
            self._build()

    def test_moving_branch_cannot_replace_checkpoint_ref(self) -> None:
        moving = "refs/remotes/origin/codex/example"
        self._git("update-ref", moving, self.head)
        with self.assertRaisesRegex(MODULE.CheckpointError, "dedicated executor checkpoint"):
            self._build(checkpoint_remote_ref=moving)

    def test_remote_mismatch_fails(self) -> None:
        (self.repo / "second.txt").write_text("second", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "second [agent:CODEX]")
        with self.assertRaisesRegex(MODULE.CheckpointError, "checkpoint remote mismatch"):
            self._build(baseline=self.head)

    def test_failed_test_marks_checkpoint_unbuildable(self) -> None:
        payload = self._build(tests=["creative_suite=FAIL"])
        self.assertFalse(payload["buildable"])

    def test_receipt_output_is_confined(self) -> None:
        safe = MODULE._safe_output(self.repo, Path(".creative-evidence/checkpoint.json"))
        self.assertEqual(safe.parent.name, ".creative-evidence")
        with self.assertRaisesRegex(MODULE.CheckpointError, "must stay"):
            MODULE._safe_output(self.repo, Path("outside.json"))


if __name__ == "__main__":
    unittest.main()
